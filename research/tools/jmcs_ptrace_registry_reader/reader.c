#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>

#ifndef PTRACE_TEST
/* Values from NDK r23c sysroot/usr/include/linux/ptrace.h, included by sys/ptrace.h. */
_Static_assert(PTRACE_PEEKDATA == 2, "unexpected NDK PTRACE_PEEKDATA ABI value");
_Static_assert(PTRACE_ATTACH == 16, "unexpected NDK PTRACE_ATTACH ABI value");
_Static_assert(PTRACE_DETACH == 17, "unexpected NDK PTRACE_DETACH ABI value");
#endif

#define MAX_ENTRIES 128u
#define MAX_MAPS 4096u
#define MAX_WORDS_PER_PASS (2u + 5u * MAX_ENTRIES)
#define MAX_PASSES 2u
#define MAX_TARGET_BYTES (MAX_PASSES * MAX_WORDS_PER_PASS * 4u)

typedef struct { uint32_t lo, hi; } Range;
typedef struct { uint32_t node, next, bookkeeping, iface, matcher, attach; } Entry;
typedef struct { uint32_t manager, head; size_t n; Entry e[MAX_ENTRIES]; } Snapshot;
typedef struct { Range ranges[MAX_MAPS]; size_t nranges; size_t bytes; } ReadContext;

typedef struct {
    int (*attach)(pid_t);
    pid_t (*wait_stop)(pid_t, int *);
    long (*peek)(pid_t, uint32_t);
    int (*detach)(pid_t, int);
} TraceOps;

typedef struct {
    pid_t pid;
    int attached;
    int wait_succeeded;
    int detach_attempted;
    int detach_succeeded;
    uint64_t attach_start_ns;
    uint64_t detach_end_ns;
    ReadContext reads;
} Session;

static volatile sig_atomic_t interrupted;
#ifndef PTRACE_TEST
static void on_signal(int sig) { (void)sig; interrupted = 1; }
#endif

static int range_add(ReadContext *c, uint32_t lo, uint32_t hi) {
    if (lo >= hi || c->nranges == MAX_MAPS) return -1;
    c->ranges[c->nranges++] = (Range){lo, hi};
    return 0;
}

static int mapped(const ReadContext *c, uint32_t p, size_t n) {
    if (!p || n > UINT32_MAX - p) return 0;
    for (size_t i = 0; i < c->nranges; ++i)
        if (p >= c->ranges[i].lo && p + n <= c->ranges[i].hi) return 1;
    return 0;
}

static int ptr_ok(uint32_t p) { return p != 0 && (p & 3u) == 0; }

#ifdef PTRACE_TEST
static unsigned char test_memory[65536];
static int test_attach_error, test_wait_error, test_detach_error;
static int test_wait_status, test_errno_mode, test_last_detach_signal, test_peek_error;
static unsigned test_attach_calls, test_wait_calls, test_peek_calls, test_detach_calls, test_fail_peek_at;
static int test_attach(pid_t p) { (void)p; ++test_attach_calls; if (test_attach_error) { errno=test_attach_error; return -1; } return 0; }
static pid_t test_wait(pid_t p, int *s) { ++test_wait_calls; if (test_wait_error) { errno=test_wait_error; return -1; } *s=test_wait_status ? test_wait_status : (SIGSTOP << 8) | 0x7f; return p; }
static long test_peek(pid_t p, uint32_t a) { (void)p; ++test_peek_calls; if (test_fail_peek_at && test_peek_calls==test_fail_peek_at) { errno=test_peek_error ? test_peek_error : EFAULT; return -1; } if (a > sizeof(test_memory)-4) { errno=EFAULT; return -1; } uint32_t v; memcpy(&v,test_memory+a,4); if (test_errno_mode == 1) errno=EIO; return (long)(int32_t)v; }
static int test_detach(pid_t p, int sig) { (void)p;test_last_detach_signal=sig;++test_detach_calls;if(test_detach_error){errno=test_detach_error;return -1;}return 0; }
#define LIVE_OPS ((TraceOps){test_attach,test_wait,test_peek,test_detach})
#else
static int live_attach(pid_t p) { return ptrace(PTRACE_ATTACH,p,NULL,NULL) == -1 ? -1 : 0; }
static pid_t live_wait(pid_t p, int *status) { return waitpid(p,status,0); }
static long live_peek(pid_t p, uint32_t a) { errno=0; long v=ptrace(PTRACE_PEEKDATA,p,(void *)(uintptr_t)a,NULL); if(v == -1 && errno != 0) return -1; return v; }
static int live_detach(pid_t p, int sig) { return ptrace(PTRACE_DETACH,p,NULL,(void *)(intptr_t)sig) == -1 ? -1 : 0; }
#define LIVE_OPS ((TraceOps){live_attach,live_wait,live_peek,live_detach})
#endif

static int read_word(Session *s, const TraceOps *ops, uint32_t addr, uint32_t *out) {
    if (!ptr_ok(addr) || !mapped(&s->reads, addr, 4)) { errno=EFAULT; return -1; }
    errno=0;
    long value=ops->peek(s->pid,addr);
    int e=errno;
    if(interrupted) { errno=EINTR; return -1; }
    if(value == -1 && e != 0) { errno=e; return -1; }
    *out=(uint32_t)(unsigned long)value;
    s->reads.bytes += 4;
    return 0;
}

static int walk(Session *s, const TraceOps *ops, uint32_t cell, Snapshot *snap) {
    uint32_t manager, head;
    if(read_word(s,ops,cell,&manager) || !ptr_ok(manager) || read_word(s,ops,manager+8,&head)) return -1;
    if(head && !ptr_ok(head)) { errno=EFAULT; return -1; }
    snap->manager=manager; snap->head=head; snap->n=0;
    uint32_t node=head;
    while(node) {
        if(!ptr_ok(node) || !mapped(&s->reads,node,12)) { errno=EFAULT; return -1; }
        for(size_t i=0;i<snap->n;i++) if(snap->e[i].node==node) { errno=ELOOP; return -1; }
        if(snap->n==MAX_ENTRIES) { errno=E2BIG; return -1; }
        uint32_t next, bookkeeping, iface, matcher, attach;
        if(read_word(s,ops,node,&next) || read_word(s,ops,node+4,&bookkeeping) || read_word(s,ops,node+8,&iface)) return -1;
        if(next && !ptr_ok(next)) { errno=EFAULT; return -1; }
        if(!ptr_ok(iface) || !mapped(&s->reads,iface,8)) { errno=EFAULT; return -1; }
        if(read_word(s,ops,iface,&matcher) || read_word(s,ops,iface+4,&attach)) return -1;
        snap->e[snap->n++]=(Entry){node,next,bookkeeping,iface,matcher,attach};
        node=next;
    }
    return 0;
}

static int same_snapshot(const Snapshot *a,const Snapshot *b) {
    if(a->manager!=b->manager || a->head!=b->head || a->n!=b->n) return 0;
    for(size_t i=0;i<a->n;i++) if(memcmp(&a->e[i],&b->e[i],sizeof(Entry))) return 0;
    return 1;
}

static int do_detach(Session *s,const TraceOps *ops,int sig) {
    if(!s->attached || s->detach_attempted) return s->detach_succeeded ? 0 : -1;
    s->detach_attempted=1;
    if(ops->detach(s->pid,sig)==0) s->detach_succeeded=1;
    else { fprintf(stderr,"CRITICAL_DETACH_FAILURE errno=%d\n",errno); }
    s->attached=0;
    return s->detach_succeeded ? 0 : -1;
}

#ifndef PTRACE_TEST
static int maps_file(ReadContext *c,const char *path) {
    FILE *f=fopen(path,"r"); if(!f) return -1;
    char line[2048];
    while(fgets(line,sizeof line,f)) {
        unsigned long lo,hi; char perms[5];
        if(sscanf(line,"%lx-%lx %4s",&lo,&hi,perms)==3 && perms[0]=='r' && lo<=UINT32_MAX && hi<=UINT32_MAX)
            if(range_add(c,(uint32_t)lo,(uint32_t)hi)) { fclose(f); return -1; }
    }
    fclose(f); return c->nranges ? 0 : -1;
}

static int target_ok(pid_t pid) {
    char path[64], buf[128]; snprintf(path,sizeof path,"/proc/%d/cmdline",pid);
    int fd=open(path,O_RDONLY|O_CLOEXEC); if(fd<0)return 0;
    ssize_t n=read(fd,buf,sizeof buf-1); close(fd); if(n<=0)return 0;
    buf[n]=0; return strcmp(buf,"/system/bin/jmcs")==0;
}

#endif
static uint64_t now_ns(void) { struct timespec t; if(clock_gettime(CLOCK_MONOTONIC,&t))return 0; return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec; }

static int capture(Session *s,const TraceOps *ops,uint32_t cell,Snapshot *result) {
    int status=0, success=0, detach_signal=0;
    s->attach_start_ns=now_ns();
    if(ops->attach(s->pid)) { fprintf(stderr,"ATTACH_FAILED errno=%d\n",errno); return -1; }
    s->attached=1;
    pid_t w;
    /* Once attached, finish waiting through EINTR so cleanup never races the attach stop. */
    do { w=ops->wait_stop(s->pid,&status); } while(w<0 && errno==EINTR);
    if(w!=s->pid) { fprintf(stderr,"WAIT_FAILED errno=%d\n",errno); goto cleanup; }
    if(!WIFSTOPPED(status)) { fprintf(stderr,"UNEXPECTED_WAIT_STATUS status=0x%x\n",status); goto cleanup; }
    s->wait_succeeded=1;
    int stop_sig=WSTOPSIG(status);
    if(stop_sig!=SIGSTOP) { fprintf(stderr,"UNEXPECTED_STOP_SIGNAL signal=%d (forwarding observed signal on detach)\n",stop_sig); detach_signal=stop_sig; goto cleanup; }
    if(interrupted) { fprintf(stderr,"INTERRUPTED_AFTER_ATTACH\n"); goto cleanup; }
    Snapshot first,second;
    if(walk(s,ops,cell,&first)) { fprintf(stderr,"READ_FAILED errno=%d\n",errno); goto cleanup; }
    if(interrupted) { fprintf(stderr,"INTERRUPTED_DURING_READ\n"); goto cleanup; }
    if(walk(s,ops,cell,&second)) { fprintf(stderr,"READ_FAILED errno=%d\n",errno); goto cleanup; }
    if(!same_snapshot(&first,&second)) { fprintf(stderr,"INCONSISTENT_SNAPSHOT\n"); goto cleanup; }
    *result=second;
    success=1;
cleanup:
    if(do_detach(s,ops,detach_signal)) return -1;
    return success ? 0 : -1;
}

#ifndef PTRACE_TEST
static void print_json(pid_t pid,uint32_t cell,const Snapshot *s,const Session *session) {
    uint64_t dur=session->detach_end_ns>=session->attach_start_ns ? (session->detach_end_ns-session->attach_start_ns)/1000000ull : 0;
    printf("{\"pid\":%d,\"method\":\"ptrace_peekdata\",\"mc_devs_cell\":\"0x%08" PRIx32 "\",\"manager\":\"0x%08" PRIx32 "\",\"registry_head\":\"0x%08" PRIx32 "\",\"attach_succeeded\":true,\"wait_succeeded\":true,\"detach_succeeded\":true,\"attach_duration_ms\":%" PRIu64 ",\"target_bytes_read\":%zu,\"consistency_passes\":2,\"entries\":[",pid,cell,s->manager,s->head,dur,session->reads.bytes);
    for(size_t i=0;i<s->n;i++) { const Entry *e=&s->e[i];
        printf("%s{\"index\":%zu,\"node\":\"0x%08" PRIx32 "\",\"next\":\"0x%08" PRIx32 "\",\"bookkeeping\":\"0x%08" PRIx32 "\",\"interface\":\"0x%08" PRIx32 "\",\"matcher\":\"0x%08" PRIx32 "\",\"attach\":\"0x%08" PRIx32 "\"}",i?",":"",i,e->node,e->next,e->bookkeeping,e->iface,e->matcher,e->attach);
    }
    puts("]}");
}

int main(int argc,char **argv) {
    pid_t pid=0; uint32_t cell=0; int have_cell=0;
    for(int i=1;i<argc;i++) {
        if(!strcmp(argv[i],"--pid") && i+1<argc) pid=(pid_t)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--mc-devs-cell") && i+1<argc) { cell=(uint32_t)strtoul(argv[++i],NULL,0); have_cell=1; }
        else { fprintf(stderr,"usage: %s --pid PID --mc-devs-cell ADDRESS\n",argv[0]); return 2; }
    }
    if(pid<=0 || !have_cell || !ptr_ok(cell)) { fprintf(stderr,"INVALID_ARGUMENTS\n"); return 2; }
    if(!target_ok(pid)) { fprintf(stderr,"TARGET_IDENTITY_MISMATCH\n"); return 2; }
    char path[64]; snprintf(path,sizeof path,"/proc/%d/maps",pid);
    Session session={.pid=pid};
    if(maps_file(&session.reads,path) || !mapped(&session.reads,cell,4)) { fprintf(stderr,"MAPS_OR_CELL_INVALID\n"); return 2; }
    struct sigaction sa={0}; sa.sa_handler=on_signal; sigemptyset(&sa.sa_mask);
    sigaction(SIGINT,&sa,NULL); sigaction(SIGTERM,&sa,NULL);
    Snapshot snapshot;
    int rc=capture(&session,&LIVE_OPS,cell,&snapshot);
    if(rc || !session.detach_succeeded) { if(session.detach_attempted && !session.detach_succeeded) return 3; return 1; }
    session.detach_end_ns=now_ns();
    print_json(pid,cell,&snapshot,&session);
    return 0;
}
#endif

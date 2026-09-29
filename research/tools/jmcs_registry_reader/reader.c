#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/uio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <limits.h>
#include <sys/syscall.h>

#define MAX_ENTRIES 128u
#define MAX_MAPS 4096u
#define MAX_TARGET_BYTES (2u * 2u * (8u + 20u * MAX_ENTRIES))
typedef struct { uint32_t lo, hi; } Range;
typedef struct { uint32_t node, next, bookkeeping, iface, matcher, attach; } Entry;
typedef struct { uint32_t manager, head; size_t n; Entry e[MAX_ENTRIES]; } Snapshot;
typedef struct { pid_t pid; Range maps[MAX_MAPS]; size_t nmaps; size_t requested, read; } Context;

#ifdef SYNTHETIC
static unsigned char fake_mem[65536];
static int fake_error, fake_short, fake_mutate;
static unsigned fake_reads;
static ssize_t target_read(pid_t pid, uint32_t addr, void *dst, size_t len) {
    (void)pid; ++fake_reads;
    if (fake_error) { errno=fake_error; return -1; }
    if (fake_mutate && fake_reads == 2) memset(fake_mem+0x2008,0,4);
    if (addr > sizeof(fake_mem) || len > sizeof(fake_mem)-addr) { errno=EFAULT; return -1; }
    if (fake_short && len) { memcpy(dst,fake_mem+addr,len-1); return (ssize_t)len-1; }
    memcpy(dst,fake_mem+addr,len); return (ssize_t)len;
}
#else
static ssize_t target_read(pid_t pid, uint32_t addr, void *dst, size_t len) {
#if defined(SYS_process_vm_readv)
    struct iovec local={dst,len}, remote={(void *)(uintptr_t)addr,len};
    return syscall(SYS_process_vm_readv,pid,&local,1,&remote,1,0);
#elif defined(__NR_process_vm_readv)
    struct iovec local={dst,len}, remote={(void *)(uintptr_t)addr,len};
    return syscall(__NR_process_vm_readv,pid,&local,1,&remote,1,0);
#else
#error "Target headers do not define process_vm_readv syscall number; refusing an unverified number"
#endif
}
#endif

static int add_range(Context *c,uint32_t lo,uint32_t hi) { if(lo>=hi||c->nmaps==MAX_MAPS)return -1; c->maps[c->nmaps++]=(Range){lo,hi}; return 0; }
static int mapped(Context*c,uint32_t p,size_t n) {
    if(!p || n>UINT32_MAX-p) return 0;
    for(size_t i=0;i<c->nmaps;i++) if(p>=c->maps[i].lo && p+n<=c->maps[i].hi) return 1;
    return 0;
}
static int read_exact(Context*c,uint32_t p,void*out,size_t n) {
    c->requested+=n;
    if(!mapped(c,p,n)) { fprintf(stderr,"READ_STATUS=INVALID_MAPPING\n"); return -1; }
    ssize_t r=target_read(c->pid,p,out,n); if(r>0)c->read+=(size_t)r;
    if(r==(ssize_t)n)return 0;
    if(r>=0){fprintf(stderr,"READ_STATUS=SHORT_READ\n");return -1;}
    switch(errno){case ENOSYS:fprintf(stderr,"READ_STATUS=UNSUPPORTED\n");break;case EPERM:case EACCES:fprintf(stderr,"READ_STATUS=PERMISSION_DENIED\n");break;case ESRCH:fprintf(stderr,"READ_STATUS=PID_DISAPPEARED\n");break;case EFAULT:fprintf(stderr,"READ_STATUS=EFAULT\n");break;case EINVAL:fprintf(stderr,"READ_STATUS=EINVAL\n");break;default:fprintf(stderr,"READ_STATUS=ERROR errno=%d\n",errno);}
    return -1;
}
static int ptr_ok(uint32_t p){return p && !(p&3u);}
static int walk(Context*c,uint32_t cell,Snapshot*s) {
    uint32_t mgr=0; if(read_exact(c,cell,&mgr,4))return -1;
    if(!ptr_ok(mgr)){fprintf(stderr,"ABORT=null_or_unaligned_manager\n");return -1;}
    uint32_t head=0; if(read_exact(c,mgr+8,&head,4))return -1;
    if(head && !ptr_ok(head)){fprintf(stderr,"ABORT=unaligned_head\n");return -1;}
    s->manager=mgr;s->head=head;s->n=0;
    uint32_t node=head;
    while(node){
        if(!ptr_ok(node)||!mapped(c,node,12)){fprintf(stderr,"ABORT=invalid_node\n");return -1;}
        for(size_t i=0;i<s->n;i++) if(s->e[i].node==node){fprintf(stderr,"ABORT=list_cycle\n");return -1;}
        if(s->n==MAX_ENTRIES){fprintf(stderr,"ABORT=entry_limit\n");return -1;}
        uint32_t f[3]; if(read_exact(c,node,f,sizeof f))return -1;
        if(f[0] && !ptr_ok(f[0])){fprintf(stderr,"ABORT=unaligned_next\n");return -1;}
        if(!ptr_ok(f[2])||!mapped(c,f[2],8)){fprintf(stderr,"ABORT=invalid_interface\n");return -1;}
        uint32_t cb[2]; if(read_exact(c,f[2],cb,8))return -1;
        s->e[s->n++]=(Entry){node,f[0],f[1],f[2],cb[0],cb[1]}; node=f[0];
    }
    return 0;
}
static int same(Snapshot*a,Snapshot*b){if(a->manager!=b->manager||a->head!=b->head||a->n!=b->n)return 0;for(size_t i=0;i<a->n;i++)if(a->e[i].node!=b->e[i].node||a->e[i].next!=b->e[i].next||a->e[i].iface!=b->e[i].iface)return 0;return 1;}
#ifndef SYNTHETIC
static int maps_file(Context*c,const char*path){FILE*f=fopen(path,"r");if(!f)return -1;char line[2048];while(fgets(line,sizeof line,f)){unsigned long a,b;char perm[5];if(sscanf(line,"%lx-%lx %4s",&a,&b,perm)==3&&perm[0]=='r'&&a<=UINT32_MAX&&b<=UINT32_MAX)add_range(c,(uint32_t)a,(uint32_t)b);}fclose(f);return c->nmaps?0:-1;}
static int target_ok(pid_t pid){char p[64],buf[1024];snprintf(p,sizeof p,"/proc/%d/cmdline",pid);int fd=open(p,O_RDONLY|O_CLOEXEC);if(fd<0)return 0;ssize_t n=read(fd,buf,sizeof(buf)-1);close(fd);if(n<=0)return 0;buf[n]=0;return !strcmp(buf,"/system/bin/jmcs");}
static const char* module(Context*c,uint32_t p){for(size_t i=0;i<c->nmaps;i++)if(p>=c->maps[i].lo&&p<c->maps[i].hi)return "mapped_module_unresolved";return "unmapped";}
#endif
#ifndef SYNTHETIC
int main(int argc,char**argv){pid_t pid=0;uint32_t cell=0;const char*maps=NULL;
 for(int i=1;i<argc;i++){if(!strcmp(argv[i],"--pid")&&i+1<argc)pid=(pid_t)strtol(argv[++i],0,10);else if(!strcmp(argv[i],"--mc-devs-cell")&&i+1<argc)cell=(uint32_t)strtoul(argv[++i],0,0);else if(!strcmp(argv[i],"--maps")&&i+1<argc)maps=argv[++i];else{fprintf(stderr,"usage: %s --pid PID --mc-devs-cell ADDRESS [--maps FILE]\n",argv[0]);return 2;}}
 if(pid<=0||!ptr_ok(cell)){fprintf(stderr,"ABORT=invalid_arguments\n");return 2;} if(!target_ok(pid)){fprintf(stderr,"ABORT=target_not_/system/bin/jmcs_or_pid_missing\n");return 2;}
 char proc[64];snprintf(proc,sizeof proc,"/proc/%d/maps",pid);Context c={.pid=pid};if(maps_file(&c,proc)){fprintf(stderr,"ABORT=live_maps_unreadable\n");return 2;}
 if(maps){Context saved={0};if(maps_file(&saved,maps)){fprintf(stderr,"ABORT=saved_maps_unreadable\n");return 2;}Range live[MAX_MAPS];size_t nl=c.nmaps;memcpy(live,c.maps,nl*sizeof(Range));c.nmaps=0;for(size_t i=0;i<nl;i++)for(size_t j=0;j<saved.nmaps;j++){uint32_t lo=live[i].lo>saved.maps[j].lo?live[i].lo:saved.maps[j].lo,hi=live[i].hi<saved.maps[j].hi?live[i].hi:saved.maps[j].hi;if(lo<hi)add_range(&c,lo,hi);}}
 Snapshot a,b;int consistent=0;for(int attempt=0;attempt<2;attempt++){if(walk(&c,cell,&a))return 1;if(walk(&c,cell,&b))return 1;if(same(&a,&b)){consistent=1;break;}}
 if(!consistent){fprintf(stderr,"STATUS=INCONSISTENT_SNAPSHOT\nTARGET_BYTES_REQUESTED=%zu\nTARGET_BYTES_READ=%zu\n",c.requested,c.read);return 1;}
 printf("{\"pid\":%d,\"method\":\"process_vm_readv\",\"mc_devs_cell\":\"0x%08" PRIx32 "\",\"manager\":\"0x%08" PRIx32 "\",\"registry_head\":\"0x%08" PRIx32 "\",\"consistent\":true,\"entries\":[",pid,cell,a.manager,a.head);
 for(size_t i=0;i<a.n;i++){Entry*e=&a.e[i];printf("%s{\"index\":%zu,\"node\":\"0x%08" PRIx32 "\",\"next\":\"0x%08" PRIx32 "\",\"bookkeeping\":\"0x%08" PRIx32 "\",\"interface\":\"0x%08" PRIx32 "\",\"matcher\":\"0x%08" PRIx32 "\",\"attach\":\"0x%08" PRIx32 "\",\"matcher_module\":\"%s\",\"attach_module\":\"%s\"}",i?",":"",i,e->node,e->next,e->bookkeeping,e->iface,e->matcher,e->attach,module(&c,e->matcher),module(&c,e->attach));}
 printf("],\"target_bytes_requested\":%zu,\"target_bytes_read\":%zu}\n",c.requested,c.read);return 0;}
#else
int main(void){puts("synthetic harness supplied separately");return 0;}
#endif

#define PTRACE_TEST
#include "reader.c"
#include <assert.h>

static void put32(uint32_t a,uint32_t v){memcpy(test_memory+a,&v,4);}
static void reset(unsigned n) {
    memset(test_memory,0,sizeof test_memory); test_attach_error=test_wait_error=test_detach_error=0;
    interrupted=0;
    test_wait_status=0; test_errno_mode=0; test_fail_peek_at=0; test_peek_error=0; test_last_detach_signal=0; test_attach_calls=test_wait_calls=test_peek_calls=test_detach_calls=0;
    put32(0x1000,0x2000); put32(0x2008,n?0x3000:0);
    for(unsigned i=0;i<n && i<129;i++) { uint32_t node=0x3000+i*0x20,iface=0x5000+i*0x10; put32(node,i+1<n?node+0x20:0); put32(node+4,0xdead0000+i);put32(node+8,iface);put32(iface,0x6000+i*4);put32(iface+4,0x7000+i*4); }
}
static Session session(void) { Session s={.pid=123}; assert(!range_add(&s.reads,0,sizeof test_memory)); return s; }
static void check_cleanup_error(int kind,unsigned n) {
    reset(n); Session s=session(); Snapshot out;
    if(kind==1)test_wait_error=ECHILD;
    if(kind==2)test_errno_mode=1;
    if(kind==3)put32(0x1000,0);
    if(kind==4)test_detach_error=EIO;
    (void)capture(&s,&LIVE_OPS,0x1000,&out);
    assert(test_attach_calls==1);
    assert(test_detach_calls==1); /* Every post-attach error has one cleanup attempt. */
    assert(s.detach_attempted);
}
int main(void) {
    Snapshot out; Session s;
    reset(1); s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)==0); assert(out.n==1&&out.e[0].matcher==0x6000); assert(s.wait_succeeded&&s.detach_succeeded&&test_detach_calls==1);
    reset(0); put32(0x1000,0xffffffffu); s=session(); uint32_t word=0; assert(read_word(&s,&LIVE_OPS,0x1000,&word)==0&&word==0xffffffffu); /* -1 with errno=0 is data. */
    reset(0); put32(0x1000,0xffffffffu); test_errno_mode=1; s=session(); assert(read_word(&s,&LIVE_OPS,0x1000,&word)<0&&errno==EIO); /* -1 plus errno is failure. */
    reset(0); put32(0x1000,0x2000); put32(0x2008,0xffffffffu); test_errno_mode=1; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0); assert(test_detach_calls==1);
    reset(0); test_attach_error=EPERM; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0); assert(!s.attached&&test_detach_calls==0);
    check_cleanup_error(1,1); /* wait failure */
    check_cleanup_error(2,0); /* PEEKDATA error */
    reset(2); test_fail_peek_at=9; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1); /* mid-list read failure */
    reset(1); test_fail_peek_at=1; test_peek_error=ESRCH; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1); /* target exits */
    check_cleanup_error(3,0); /* invalid pointer */
    check_cleanup_error(4,0); /* detach failure */
    reset(1); test_wait_status=(SIGTRAP<<8)|0x7f; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0); assert(test_detach_calls==1&&test_last_detach_signal==SIGTRAP);
    reset(1); test_wait_status=1; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1);
    reset(1); interrupted=1; s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1);
    reset(128); s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)==0&&out.n==128);
    reset(129); s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1);
    reset(2); put32(0x3020,0x3000); s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1);
    reset(1); put32(0x3008,0x90000); s=session(); assert(capture(&s,&LIVE_OPS,0x1000,&out)<0&&test_detach_calls==1);
    printf("ptrace synthetic checks: PASS (max target bytes %u)\n",MAX_TARGET_BYTES);
    return 0;
}

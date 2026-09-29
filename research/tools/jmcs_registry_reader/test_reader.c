#define SYNTHETIC
#define main reader_stub_main
#include "reader.c"
#undef main
#include <assert.h>

static void put32(uint32_t a,uint32_t v){memcpy(fake_mem+a,&v,4);}
static void setup(unsigned n){memset(fake_mem,0,sizeof fake_mem);fake_error=0;fake_short=0;fake_mutate=0;fake_reads=0;Context c={0};assert(!add_range(&c,0,sizeof fake_mem));put32(0x1000,0x2000);put32(0x2008,n?0x3000:0);for(unsigned i=0;i<n;i++){uint32_t node=0x3000+i*0x20,iface=0x5000+i*0x10;put32(node,i+1<n?node+0x20:0);put32(node+4,0xdead0000+i);put32(node+8,iface);put32(iface,0x6000+i*4);put32(iface+4,0x7000+i*4);}}
static int capture(unsigned n,Snapshot*s){(void)n;Context c={.pid=1};add_range(&c,0,sizeof fake_mem);return walk(&c,0x1000,s);}
int main(void){Snapshot a,b;
 setup(0);assert(capture(0,&a)==0&&a.n==0&&a.head==0);
 setup(1);assert(capture(1,&a)==0&&a.n==1&&a.e[0].matcher==0x6000);
 setup(4);assert(capture(4,&a)==0&&a.n==4);for(unsigned i=0;i<4;i++)assert(a.e[i].node==0x3000u+i*0x20u);
 setup(128);assert(capture(128,&a)==0&&a.n==128);
 setup(129);assert(capture(129,&a)<0);
 setup(1);put32(0x1000,0);assert(capture(1,&a)<0);
 setup(1);put32(0x2008,0x90000);assert(capture(1,&a)<0);
 setup(1);put32(0x3008,0x90000);assert(capture(1,&a)<0);
 setup(1);put32(0x3000,0x3000);assert(capture(1,&a)<0);
 setup(2);put32(0x3020,0x3000);assert(capture(2,&a)<0);
 setup(1);Context c={.pid=1};add_range(&c,0,sizeof fake_mem);assert(!walk(&c,0x1000,&a));fake_mutate=1;fake_reads=0;assert(!walk(&c,0x1000,&b));assert(!same(&a,&b));
 setup(0);fake_short=1;assert(capture(0,&a)<0);
 setup(0);fake_error=EPERM;assert(capture(0,&a)<0);
 setup(0);fake_error=ENOSYS;assert(capture(0,&a)<0);
 setup(0);fake_error=ESRCH;assert(capture(0,&a)<0);
 puts("synthetic reader checks: PASS");return 0;}

`timescale 1ns/1ps
// Exercise the exact generated demo wrapper. FAST=0 boots the unchanged board
// firmware with its real UART rate; FAST=1 runs all three classes with shortened
// seconds. Both modes load the unchanged real board firmware and need no PHY clocks.
module tb_board_demo_v6_1;
 parameter integer FAST=1;
 localparam integer SEC=FAST ? 400_000 : 27_000_000;
 localparam integer BAUD=FAST ? 1_800_000 : 115_200;
 localparam integer CPB=27_000_000/BAUD;
 reg clk=0,rst_n=1,key_n=1;always #18.518 clk=~clk;
 wire uart_tx;wire[5:0] led_n;tri1 sda,scl;
 gowin_demo_top #(.FIRMWARE("fw/firmware.hex"),
  .SEC_CYCLES(SEC),.BAUD(BAUD),.DEBOUNCE_CYC(FAST ? 200 : 270_000)) dut(
  .clk_27m(clk),.rst_n(rst_n),.key_n(key_n),.uart_tx(uart_tx),.oled_sda(sda),.oled_scl(scl),.led_n(led_n));
 integer cycles=0;always @(posedge clk)cycles<=cycles+1;
 reg[7:0] line[0:255];integer ll=0,bitn,k,j,commas,cls,packets,star;
 reg[7:0] ch,cs;reg[511:0] hash;
 reg post_ok=0,hash_ok=0,block50=0,block51=0;
 integer normal_seen=0,syn_seen=0,scan_seen=0,bad_checksums=0,ids_seen=0,logf;
 function integer hexval(input[7:0] c);
  begin
   if(c>="0" && c<="9")hexval=c-"0";
   else if(c>="A" && c<="F")hexval=c-"A"+10;
   else if(c>="a" && c<="f")hexval=c-"a"+10;
   else hexval=-1;
  end
 endfunction
 function contains(input[8*32-1:0] value,input integer n);
  integer a,b;reg hit;
  begin
   contains=0;
   for(a=0;a+n<=ll;a=a+1)begin
    hit=1;
    for(b=0;b<n;b=b+1)if(line[a+b]!==value[8*(n-1-b)+:8])hit=0;
    if(hit)contains=1;
   end
  end
 endfunction
 task end_line;
  begin
   if(ll>=9 && line[0]=="#" && line[2]=="P" && line[7]=="O" && line[8]=="K" && contains("37/37",5))post_ok=1;
   if(ll==79)begin
    hash=0;for(k=15;k<79;k=k+1)hash={hash[503:0],line[k]};
    if(hash=="3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515")hash_ok=1;
   end
   if(ll>3 && line[0]=="$")begin
    star=-1;cs=0;
    for(k=1;k<ll;k=k+1)if(line[k]=="*" && star<0)star=k;
    if(star<1 || star+3!=ll)bad_checksums=bad_checksums+1;
    else begin
     for(k=1;k<star;k=k+1)cs=cs^line[k];
     if(hexval(line[star+1])<0 || hexval(line[star+2])<0 || cs!=(hexval(line[star+1])*16+hexval(line[star+2])))bad_checksums=bad_checksums+1;
    end
    if(line[1]=="I" && line[2]=="D" && line[3]=="S")begin
     commas=0;cls=-1;packets=0;
     for(k=0;k<ll;k=k+1)begin
      if(line[k]==",")commas=commas+1;
      else if(commas==2)cls=line[k]-"0";
      else if(commas==4 && line[k]>="0" && line[k]<="9")packets=packets*10+line[k]-"0";
     end
     ids_seen=ids_seen+1;
     if(packets>0)case(cls)
      0:normal_seen=normal_seen+1;
      1:syn_seen=syn_seen+1;
      2:scan_seen=scan_seen+1;
     endcase
    end
    if(line[1]=="B" && line[2]=="L" && line[3]=="K")begin
     if(contains("192.168.10.50",13))block50=1;
     if(contains("192.168.10.51",13))block51=1;
    end
   end
   ll=0;
  end
 endtask
 initial begin
  if(FAST)logf=$fopen("sim/out/demo_uart.log","w");
  else logf=$fopen("sim/out/demo_post_uart.log","w");
  if(!logf)$fatal(1,"Cannot open demo UART log");
  forever begin
   @(negedge uart_tx);repeat(CPB/2)@(posedge clk);
   if(!uart_tx)begin
    for(bitn=0;bitn<8;bitn=bitn+1)begin repeat(CPB)@(posedge clk);ch[bitn]=uart_tx;end
    repeat(CPB)@(posedge clk);$fwrite(logf,"%c",ch);
    if(ch==10)begin $fflush(logf);end_line;end
    else if(ch!=13 && ll<256)begin line[ll]=ch;ll=ll+1;end
   end
  end
 end
 initial begin
  if(!FAST)begin
   wait(post_ok && hash_ok);repeat(100)@(posedge clk);
   if(dut.u_top.trap || led_n!==6'b111111)$fatal(1,"Demo board POST trap/LED failure");
   $display("PASS V6_1_BOARD_DEMO_POST board_firmware=unchanged UART=115200 POST=37/37 model_hash=OK PHY_clocks=none");
   $finish;
  end else begin
   wait(post_ok && hash_ok);repeat(SEC/4)@(posedge clk);
   key_n=0;repeat(SEC/3)@(posedge clk);key_n=1;
   wait(normal_seen>=2 && syn_seen>=2 && scan_seen>=2 && block50 && block51);
   repeat(100)@(posedge clk);
   if(dut.u_top.trap || led_n!==6'b111111 || bad_checksums)$fatal(1,"Demo trap/LED/checksum error");
   if(dut.u_top.g_selftest.u_eth.n_sensor_drop || !dut.u_top.g_selftest.u_eth.n_sensor_fwd || dut.u_top.g_selftest.u_eth.n_no_verdict)$fatal(1,"Demo sensor/verdict failure");
   $display("PASS V6_1_BOARD_DEMO_ALL3 POST=37/37 normal=%0d syn=%0d scan=%0d block50=OK block51=OK checksums=OK PHY_clocks=none",normal_seen,syn_seen,scan_seen);
   $finish;
  end
 end
 initial begin
  repeat(FAST ? 26*SEC : 5_000_000)@(posedge clk);
  $fatal(1,"Demo timeout POST=%0b hash=%0b IDS=%0d classes=%0d/%0d/%0d blocks=%0b/%0b",post_ok,hash_ok,ids_seen,normal_seen,syn_seen,scan_seen,block50,block51);
 end
endmodule

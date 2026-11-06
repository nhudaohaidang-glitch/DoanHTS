"""Create an isolated onboard CPU/AI traffic demo; no LAN8720 or RMII ports."""
from pathlib import Path
from xml.sax.saxutils import escape

root=Path(__file__).resolve().parent
folder=root/'build/gowin_demo';folder.mkdir(parents=True,exist_ok=True)
fw=(root/'fw/firmware.hex').as_posix()
if not Path(fw).is_file():raise SystemExit('Missing V6 firmware.hex')
wrapper='''module gowin_demo_top #(
 parameter FIRMWARE = "FIRMWARE_PATH",
 parameter integer SEC_CYCLES = 27_000_000,
 parameter integer BAUD = 115_200,
 parameter integer DEBOUNCE_CYC = 270_000
)(
 input clk_27m, input rst_n, input key_n, output uart_tx,
 inout oled_sda, inout oled_scl, output [5:0] led_n);
 tangnano9k_top #(.FIRMWARE(FIRMWARE),.SELFTEST(1),.REF_METER(0),
 .SEC_CYCLES(SEC_CYCLES),.BAUD(BAUD),.DEBOUNCE_CYC(DEBOUNCE_CYC)) u_top (
 .clk_27m(clk_27m),.rst_n(rst_n),.key_n(key_n),.uart_tx(uart_tx),
 .oled_sda(oled_sda),.oled_scl(oled_scl),.led_n(led_n),
 .a_ref_clk(1'b0),.a_crs_dv(1'b0),.a_rxd(2'b00),.a_tx_en(),.a_txd(),
 .b_ref_clk(1'b0),.b_crs_dv(1'b0),.b_rxd(2'b00),.b_tx_en(),.b_txd());
endmodule
'''.replace('FIRMWARE_PATH',fw.replace('"','\\"'))
(folder/'gowin_demo_top.v').write_text(wrapper)
sources=[s.strip() for s in (root/'sources.f').read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
sources+=['rtl/board/tangnano9k_top.v','build/gowin_demo/gowin_demo_top.v']
files='\n'.join(' <File path="'+escape(p)+'" type="file.verilog" enable="1"/>' for p in sources)
files+='\n <File path="board/tangnano9k_demo.cst" type="file.cst" enable="1"/>'
files+='\n <File path="board/tangnano9k_demo.sdc" type="file.sdc" enable="1"/>'
project='''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE gowin-fpga-project>
<Project><Template>FPGA</Template><Version>5</Version>
<Device name="GW1NR-9C" pn="GW1NR-LV9QN88PC6/I5">gw1nr9c-004</Device>
<FileList>FILES</FileList></Project>
'''.replace('FILES',files)
p=root/'gateway_phan1_v6_1_demo.gprj';p.write_text(project)
print('Created:',p)
print('Top: gowin_demo_top; system clock 27 MHz; UART 115200 8N1; SELFTEST=1')
print('Generated header traffic stays inside FPGA. This does not test physical Ethernet or replay the training PCAPs.')
print('MAC project and wrapper remain unchanged. Run demo Synthesize/Place & Route and collect its report before board testing.')

# Synthesis only for an internal AI component. Not a physical board top.
set root [file normalize [file join [file dirname [info script]] ..]]
cd $root
set_device GW1NR-LV9QN88PC6/I5 -device_version C
add_file rtl/ai_core_model_v6.v
add_file gowin/constraints/ai_core.sdc
set_option -top_module ai_core
set_option -output_base_name ai_core_v6
run syn

import importlib, platform, shutil
print('Python',platform.python_version())
for name in ('numpy','sklearn','scapy','paho.mqtt.client','serial'):
    module=importlib.import_module(name)
    print('OK',name,getattr(module,'__version__','imported'))
for name in ('iverilog','vvp','mosquitto','tcpdump','ip'):
    print(name,shutil.which(name) or 'MISSING (needed for Ubuntu lab/RTL)')

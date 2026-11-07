import argparse,json,time
import paho.mqtt.client as mqtt
p=argparse.ArgumentParser();p.add_argument('--host',default='198.18.0.1');p.add_argument('--port',type=int,default=1883);a=p.parse_args()
c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='p2-observer')
def connected(client,user,flags,reason,properties):
    if reason.is_failure:raise RuntimeError(str(reason))
    client.subscribe('lab/temperature',qos=1)
def received(client,user,message):
    try:payload=json.loads(message.payload)
    except (ValueError,UnicodeDecodeError):payload={'invalid':True}
    print(json.dumps({'received_at':time.time(),'topic':message.topic,'payload':payload}),flush=True)
c.on_connect=connected;c.on_message=received
c.connect(a.host,a.port,10);c.loop_forever()

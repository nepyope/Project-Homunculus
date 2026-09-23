BOM for Homunculus Glove
========================

## Nuts & Bolts 

| M2 | screw set | 1 set | [Amazon](https://amzn.eu/d/cVf2toH) | hand

## Straps & cable management

| Item | Specifications | Quantity | Reference | Details
|-|-|-|-|-
| Velcro finger straps | reusable hook-and-loop ties, 4 in, black | 1 pack of 180 | [Amazon](https://www.amazon.com/dp/B0CJ52WJZY) | hold each finger segment to the exoskeleton
| Cable holders (zip ties) | 100 × 2.5 mm, black | 1 pack of 1000 | [Amazon](https://www.amazon.com/dp/B078NT5F2B) | route the JST cables along the fingers

## PCB
Create an account for [JLCPCB](https://jlcpcb.com/) and place an order for `homunculus_pcb`. Add gerber file and select PCB assembly, in the next screen paste BOM and POS for teleop device and connectors

## Encoders

The PCB's sensor headers are JST **SM03B-SRSS-TB** (SH series, 1.0 mm pitch, 3-pin, side entry). The cables need JST SH 1.0 mm 3-pin plugs (**SHR-03V-S-B** housing, **SSH-003T-P0.2** contacts) on both ends, wired *same direction* (pin 1 to pin 1). Not JST-XH or PH (2.5 / 2.0 mm), those won't fit.

| Item | Specifications | Quantity | Reference | Details
|-|-|-|-|-
| Magnets | neodymium disc, 3 × 2 mm, standard (axially magnetised, not diametric) | 23 | [AliExpress](https://www.aliexpress.com/item/1005001580880407.html) |  1x joint
| SS49E linear hall sensors |  | 28 | [Amazon](https://amzn.eu/d/aemjs7f) | 1x joint (hand + wrist), 2x joint (upper arm)
| JST SH 1.0 mm cables | 3 pins, double-ended, same direction, 28 AWG - length : 10cm | 1 set of 10 | [AliExpress](https://www.aliexpress.com/w/wholesale-JST-SH1.0-3P-double-head-same-direction.html)
|               | 3 pins, same direction - length : 15cm | 1 set of 10 | [AliExpress](https://www.aliexpress.com/w/wholesale-JST-SH1.0-3P-double-head-same-direction.html)
|               | 3 pins, same direction - length : 20cm | 2 sets of 10 | [AliExpress](https://www.aliexpress.com/w/wholesale-JST-SH1.0-3P-double-head-same-direction.html)
|               | 3 pins, same direction - length : 30cm | 1 set of 10 | [AliExpress](https://www.aliexpress.com/w/wholesale-JST-SH1.0-3P-double-head-same-direction.html)


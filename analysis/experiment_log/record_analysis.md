# work log: $^{131}$Ce

## 实验信息

### 反应道

1. 19F + 116Sn ：$0.9mg/cm^{2}\ ^{116}Sn + 5.5mg/cm^2 Au$ @ 85MeV 1p3n
   ![img](./figures/19F+116Sn.png)

### 实验设置

#### 探测器放置

##### Ge

1. Ge map

![img](<./figures/Ge map.png>)
2. Ge 采集卡频率

![img](./figures/Ge采集卡.png)

##### CsI

1. CsI map

![img](<./figures/CsI map.png>)
2. CsI 采集卡频率

![img](<./figures/CsI 采集卡.png>)

### Important information

#### start -> finish

1. Start time: 20250607-1738-**run6015**

   ![](./figures/experiment_start.png) 

2. finish time: 20250609-1344-**run6079**

   ![](./figures/experiment_finish.png)

3. Run summary

   1. > 1. 2025-06-07: runs 6015–6030
      > 2. Invalid run: 6027
      > 3. Runs shorter than 3 min: 6016, 6020–6023

      ![](../run_log/figures/gantt_2025-06-07.svg)

   2. > 1. 2025-06-08: runs 6031–6064
      > 2. Invalid run: None
      > 3. Runs shorter than 3 min: 6042, 6046, 6047, 6053

      ![](../run_log/figures/gantt_2025-06-08.svg)

   3. > 1. 2025-06-09: runs 6065–6079
      > 2. Invalid run: None
      > 3. Runs shorter than 3 min: None

      ![](../run_log/figures/gantt_2025-06-09.svg)


#### Events

1.  ==Unexpected events.==  20260607-1916. Bad detectors were CsI(Ti), specially for 
   1. cid=1, mod= 0, ch=10, 11, 12, 13, 14, 15.
   2. cid=1, mod=1, ch=12, 13, 14, 15.
   3. cid=1, mod=6, all channels.
2.  ==Normal events.==  20250607-1946: Filling LN to HPGe.
3.  ==Normal events.==  20250607-2100: Filling LN to HPGe.
4. ==Unexpected events.==  Removed cid=1, mod=1, ch=14, 15.
5. ==Unexpected events.== (cid, mod, ch)=(1, 1, 14), (1, 1, 15), (1, 3, 1), (1, 3, 2), (1, 3, 4) had problems. Those are CsI. 
6.   
7. ==Unexpected events.== charge module: 20250608-1419- Module 8 was changed to module 9 in crate_1 of CsI from **run6052**.

![img](./figures/CsI中途更换采集卡.png)

2. 

# Work Log: $^{131}$Ce

## 1. Experimental Information

### 1.1 Reaction Channel

1. **Reaction:** $^{19}$F + $^{116}$Sn
   - **Target:** 0.9 mg/cm² $^{116}$Sn + 5.5 mg/cm² Au
   - **Beam energy:** 85 MeV
   - **Evaporation channel:** 1p3n

   ![img](./figures/19F+116Sn.png)

### 1.2 Experimental Setup

#### 1.2.1 Detector Configuration

##### HPGe Detectors

1. **Ge detector map**

   ![img](<./figures/Ge map.png>)

2. **Ge digitizer frequency**

   ![img](./figures/Ge采集卡.png)

##### CsI Detectors

1. **CsI detector map**

   ![img](<./figures/CsI map.png>)

2. **CsI digitizer frequency**

   ![img](<./figures/CsI 采集卡.png>)

## 2. Experimental Run Log

### 2.1 Experiment Duration

1. **Start time:** 2025-06-07 17:38 — **Run 6015**

   ![](./figures/experiment_start.png)

2. **End time:** 2025-06-09 13:44 — **Run 6079**

   ![](./figures/experiment_finish.png)

### 2.2 Run Summary

1. **2025-06-07: Runs 6015–6030**
   - Invalid run: 6027
   - Runs shorter than 3 min: 6016, 6020–6023

   ![](../run_log/figures/gantt_2025-06-07.svg)

2. **2025-06-08: Runs 6031–6064**
   - Invalid runs: None
   - Runs shorter than 3 min: 6042, 6046, 6047, 6053

   ![](../run_log/figures/gantt_2025-06-08.svg)

3. **2025-06-09: Runs 6065–6079**
   - Invalid runs: None
   - Runs shorter than 3 min: None

   ![](../run_log/figures/gantt_2025-06-09.svg)

### 2.3 Significant Events

1. **2025-06-07 17:38.** <span style="background-color: #90EE90;">Routine operation</span>: Experiment started.

2. **2025-06-07 18:32.** ==Issue / intervention==: Errors detected in CsI(Ti) channels: cid=1, mod=1, ch=14, 15.

3. **2025-06-07 19:16.** ==Issue / intervention==: Multiple CsI(Ti) channels exhibited errors, particularly:
   - cid=1, mod=0, ch=10–15.
   - cid=1, mod=1, ch=12–15.
   - cid=1, mod=6, all channels.

4. **2025-06-07 19:46.** <span style="background-color: #90EE90;">Routine operation</span>: Liquid nitrogen (LN₂) refilled for the HPGe detectors.

5. **2025-06-07 19:46.** ==Issue / intervention==: High-voltage (HV) problems were observed in CsI detector rings 1 and 6. Additional HV/PIN-related issues affected cid=1, mod=1, ch=14, 15.

6. **2025-06-07 20:08.** ==Issue / intervention==: Errors detected in cid=1, mod=3, ch=1–3.

7. **2025-06-07 21:00.** <span style="background-color: #90EE90;">Routine operation</span>: Liquid nitrogen refilled for the HPGe detectors.

8. **2025-06-07 21:53.** ==Issue / intervention==: Channels cid=1, mod=1, ch=14, 15 were removed from data acquisition.

9. **2025-06-07 23:45.** ==Issue / intervention==: The data acquisition system required a restart. Run 6029 was terminated abnormally, and runs 6030 and 6031 were used for debugging.

10. **2025-06-08 00:16.** <span style="background-color: #90EE90;">Routine operation</span>: The `inrata` function for cid=1, mod=8 was enabled.

11. **2025-06-08 05:31.** ==Issue / intervention==: The accelerator malfunctioned. Run 6039 was used to record decay data.

12. **2025-06-08 05:52.** ==Issue / intervention==: The accelerator remained out of operation. Run 6040 was used to record decay data.

13. **2025-06-08 06:47.** ==Issue / intervention==: During the accelerator downtime, the detector-to-target distances were adjusted (#15: +3 cm; #36 and #39: +2 cm). Low-energy γ-ray absorbers were also installed on detectors #27 and #28.

14. **2025-06-08 06:47.** <span style="background-color: #90EE90;">Routine operation</span>: Liquid nitrogen refilled.

15. **2025-06-08 09:15.** <span style="background-color: #90EE90;">Routine operation</span>: Accelerator operation was restored, and beam delivery resumed.

16. **2025-06-08 09:37.** ==Issue / intervention==: A low-energy γ-ray absorber was added to the detector corresponding to cid=0, mod=0, ch=8.

17. **2025-06-08 10:12.** ==Issue / intervention==: The configuration of cid=1, mod=8 was modified due to a low count rate.

18. **2025-06-08 14:19.** ==Issue / intervention==: The CsI electronics modules in crate 1 were rearranged. Module 8 was replaced by module 9, while the original module 9 was relocated to a position behind module 7. The new configuration was applied starting from **run 6052**.

   ![img](./figures/CsI中途更换采集卡.png)

19. **2025-06-08 14:19.** ==Issue / intervention==: HPGe detector #27 lost its high-voltage supply.

20. **2025-06-08 15:10.** ==Issue / intervention==: Channel cid=0, mod=2, ch=10 (5C) was included in data acquisition despite 5C being a known faulty segment of the CLOVER detector.

21. **2025-06-08 17:51.** ==Issue / intervention==: The accelerator malfunctioned. Run 6057 was used to record decay data.

22. **2025-06-08 20:13.** <span style="background-color: #90EE90;">Routine operation</span>: Liquid nitrogen refilled.

23. **2025-06-09 02:24.** ==Issue / intervention==: The accelerator malfunctioned. Run 6067 was used to record decay data.

24. **2025-06-09 07:50.** <span style="background-color: #90EE90;">Routine operation</span>: Liquid nitrogen refilled.

25. **2025-06-09 09:32.** <span style="background-color: #90EE90;">Routine operation</span>: Beam delivery resumed.

26. **2025-06-09 13:51.** <span style="background-color: #90EE90;">Routine operation</span>: Experiment concluded.
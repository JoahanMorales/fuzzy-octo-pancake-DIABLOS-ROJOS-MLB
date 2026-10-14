# Contrastes exploratorios por conteo y altitud

demo_data: false

Exploratory observational contrast, not an identified causal effect or pitch-selection policy. Coach intent, hitter quality, health and other unmeasured confounders remain. Global target, identity and density preparation is transductive. Density is reconstructed from whole-game observations and is not a verified prospectively available pre-pitch measurement. Bootstrap intervals describe held-out pitcher composition conditional on one fitted forest, not model/causal uncertainty. Current-pitch movement, location, outcome and derived scores are excluded from covariates.

Tratamiento: bola rompiente menos cambio/splitter; menor xRV es mejor para el pitcher. Los intervalos describen composición de pitchers del holdout con el bosque fijo. No son intervalos de identificación causal ni una recomendación de selección.

```csv
altitude,count_bucket,n_total,n_supported,n_offspeed,n_breaking,pitchers,contrast_bb_minus_offspeed,composition_ci_lo,composition_ci_hi,status,demo_data,evidence
No Altitude,ahead,156,130,37,93,30,-0.007756383748725279,-0.009958338656005544,-0.005862280844195547,exploratory,False,observational_transductive
No Altitude,even,208,171,58,113,31,-0.00945632274684687,-0.01191108667399371,-0.006956014397426219,exploratory,False,observational_transductive
No Altitude,behind,94,81,28,53,25,,,,insufficient_support,False,observational_transductive
Medium Altitude,ahead,41,37,14,23,9,,,,insufficient_support,False,observational_transductive
Medium Altitude,even,63,61,13,48,11,,,,insufficient_support,False,observational_transductive
Medium Altitude,behind,26,26,4,22,8,,,,insufficient_support,False,observational_transductive
Extreme Altitude,ahead,70,63,26,37,21,,,,insufficient_support,False,observational_transductive
Extreme Altitude,even,114,111,42,69,24,-0.004596637018828907,-0.007756162190806482,-0.0003321888487784154,exploratory,False,observational_transductive
Extreme Altitude,behind,64,60,26,34,18,,,,insufficient_support,False,observational_transductive
```

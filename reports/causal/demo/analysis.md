# Contrastes exploratorios por conteo y altitud

demo_data: true

Exploratory observational contrast, not an identified causal effect or pitch-selection policy. Coach intent, hitter quality, health and other unmeasured confounders remain. Global target, identity and density preparation is transductive. Density is reconstructed from whole-game observations and is not a verified prospectively available pre-pitch measurement. Bootstrap intervals describe held-out pitcher composition conditional on one fitted forest, not model/causal uncertainty. Current-pitch movement, location, outcome and derived scores are excluded from covariates.

Tratamiento: bola rompiente menos cambio/splitter; menor xRV es mejor para el pitcher. Los intervalos describen composición de pitchers del holdout con el bosque fijo. No son intervalos de identificación causal ni una recomendación de selección.

```csv
altitude,count_bucket,n_total,n_supported,n_offspeed,n_breaking,pitchers,contrast_bb_minus_offspeed,composition_ci_lo,composition_ci_hi,status,demo_data,evidence
No Altitude,ahead,46,46,19,27,9,,,,insufficient_support,True,observational_transductive
No Altitude,even,87,86,34,52,9,-0.0008417423018464957,-0.005194559210505282,0.0029489081532043044,exploratory,True,observational_transductive
No Altitude,behind,52,51,28,23,9,,,,insufficient_support,True,observational_transductive
Medium Altitude,ahead,83,82,42,40,8,-0.011669582913461329,-0.01650285733175555,-0.007173675944716735,exploratory,True,observational_transductive
Medium Altitude,even,117,116,57,59,8,0.0036250622586955833,-0.0011556176150298303,0.009771743267065236,exploratory,True,observational_transductive
Medium Altitude,behind,105,101,44,57,8,0.010919685205994562,0.006188942924151193,0.015756717424754842,exploratory,True,observational_transductive
Extreme Altitude,ahead,62,57,40,17,9,,,,insufficient_support,True,observational_transductive
Extreme Altitude,even,78,77,45,32,10,0.03568849366030545,0.03147251131998072,0.04142683675283942,exploratory,True,observational_transductive
Extreme Altitude,behind,37,35,26,9,9,,,,insufficient_support,True,observational_transductive
```

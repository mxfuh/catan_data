# Catan-Prognose

Sobald in `catan_data.xlsx` für ein Spiel alle drei Zeilen mit Pre-Game-Daten stehen, aber noch kein Score,
schickt der VPS eine Prognose (Score, Sonder-SP, Platz, Siegchance) per Discord und Mail an MF, JHC und PF.
Zwei Varianten: mit und ohne One-Hot-Spieler-Variable.

**Pre-Game vollständig heißt:** `position`, `desert`, `sum`, `count_num`, `count_res`, alle `p_sum_*`, `port_*`, `prox_port_*`
in allen drei Zeilen gefüllt. Fehlt etwas, kommt (noch) keine Prognose; nach einer Korrektur kommt eine aktualisierte.

**Modell:** NN 64-32 (Softplus, Dropout 0.3, AdamW wd 1.0, 80 Epochen full-batch), Ensemble aus 5 Seeds, zwei Outputs
(score, special; maskierter Loss, weil special in frühen Spielen fehlt). Trainiert nur neu, wenn sich die
abgeschlossenen Spiele ändern. Die Fehlerangabe in der Nachricht ist Out-of-Fold (Spiele bleiben zusammen).

**Lokal testen** (gibt nur aus, sendet nichts):

    python predict/catan_predict.py --data catan_data.xlsx --state /tmp/catan-state --force

**VPS:** `~/catan/run.sh` per `catan-predict.timer` alle 3 Minuten: holt `main`, startet das Skript mit `--notify`.
Bei unveränderter Excel endet der Lauf sofort. State, Modell und `config.json` (Empfänger) liegen in `~/catan/state/`.

**Prognose-Archiv (Form-Tab):** Jede verschickte Prognose landet zusätzlich in `predict/predictions.csv`
(`source=live`). Der Prognose-Lauf committet und pusht nur diese Datei auf `main`. Klappt der Push nicht, versucht er es
beim nächsten Lauf erneut (die Werte liegen auch im State). Für ältere Spiele gibt es rückgerechnete Out-of-Fold-Werte
(`source=oof`, `computed` = Rechendatum), die das Dashboard mit Sternchen bzw. gestrichelt markiert:

    python predict/catan_predict.py --data catan_data.xlsx --state /tmp/catan-state --backfill

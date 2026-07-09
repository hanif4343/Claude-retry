# Claude API Retry Runner (Step-by-step, Resume-able, Time apni set korben)

Boro kaj ke step e vage kore, rate limit e porleo jekhane theme geche shekhan theke
continue kore. Kokhon chalbe seta apni **`config.json`** file e likhben — YAML/cron
kichu chuute hobe na, jekhono change korte parben.

## 1. Apnar kaj set korun

`tasks.json` e apnar boro kajta chotto chotto step e vagiye likhun:

```json
[
  { "id": 1, "prompt": "Prothom step er prompt" },
  { "id": 2, "prompt": "Duitiyo step er prompt" }
]
```

## 2. Kokhon chalbe - eta apni set korben

`config.json` file ta:

```json
{
  "run_times_bd": ["01:00", "06:00"],
  "tolerance_minutes": 15
}
```

- `run_times_bd`: Bangladesh time e (24-hour, `HH:MM`) apni je somoy(gulo) e
  chalate chan seta likhun. Jotogulo lagbe totogulo add/remove korte parben.
  Example: `["01:00", "06:00", "14:30"]`
- Change korte hole shudhu ei file edit kore commit/push korun - kono YAML
  chuute hobe na.
- `tolerance_minutes`: koto minute agepiche hole o "match" dhorbe (default 15,
  karon GitHub free scheduler kokhono kokhono 5-15 min late hoy)

Kivabe kaj kore: workflow ta background e protidin **15 minute por por** nijeke
check kore - "ekhon ki config.json e deya kono somoy?" Mile gele kaj shuru hoy,
na mille kichu na kore chup chap ber hoye jay (tai extra API call/limit khoroch
hoy na).

## 3. API key GitHub Secret e rakhun

1. Repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**
2. Name: `ANTHROPIC_API_KEY`, Value: apnar actual key
3. Save

## 4. Kaj kivabe resume hoy

- Protibar run e script `progress.json` check kore, kotodur hoyeche seta dekhe
- Jekhane theme gechilo, shekhan theke porer step shuru kore (age'r step abar hoy na)
- Protyekta step sesh hole shathe shathe progress save + repo te commit hoye jay
- Rate limit khele run wait kore (5 minute porjonto), tarpor o na hole run ta
  nijei bondho hoye jay - porer somoy (jeta config.json e likha ache) automatic
  continue kore

## 5. Manually chalate / result dekhte

- Manually chalate: repo -> **Actions** tab -> "Claude API Task Runner" -> **Run workflow**
  (eta somoy check na kore shorashori chalabe)
- Result: repo te `progress.json` file e shob step er output thake (`results` field e)
- Kaj shesh hole `progress.json` e `"done": true` dekhaben

## Local e test korte

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="apnar-key"
python run.py
```

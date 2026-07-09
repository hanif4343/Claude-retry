"""
Claude API kaj-runner: boro kaj ke step-by-step (tasks.json) e vage kore chalay.

Kaj kivabe hoy:
1. tasks.json theke shob step porde
2. progress.json dekhe kotodur hoyeche seta ber kore
3. jekhane sesh hoyeche shekhan theke suru kore (prothom theke abar suru hoy na)
4. protyekta step sesh hoyar por progress.json e save kore rakhe
5. rate limit e porle:
   - olpo shomoy (RETRY_WAIT_CAP_SECONDS er kom) wait korte hole, ei run eii wait kore continue kore
   - beshi shomoy lagle, ei run bondho kore dey (progress soho) - porer scheduled run
     (1 AM ba 6 AM, jeta apni set korben) shekhan theke continue korbe
6. Shob step sesh hole progress.json e "done": true likhe dey

Tai ekbar rate limit khele, porer baar abar prothom theke shuru hobe na -
jekhane theme geche shekhan theke e cholbe.
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta
import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1000

# Ekta single run e (ekbar workflow chalar somoy) rate limit er jonno max koto
# shomoy wait kora hobe. Er beshi wait korte hole, run ta বন্ধ kore progress save
# kore rakhe - porer scheduled run continue korbe. (GitHub free runner max ~6 ghonta)
RETRY_WAIT_CAP_SECONDS = 5 * 60  # 5 minute
DEFAULT_WAIT_SECONDS = 60

TASKS_FILE = "tasks.json"
PROGRESS_FILE = "progress.json"
CONFIG_FILE = "config.json"

BD_OFFSET = timedelta(hours=6)  # Bangladesh = UTC+6


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_scheduled_time_now(config, progress) -> bool:
    """config.json e deya run_times_bd er shathe ekhoner (Bangladesh) shomoy
    mile kina check kore. Match korle True, r shathe shathe deduplicate korar
    jonno progress.json e "last_run_slot" save kore rakhe (jate ekta slot e
    duibar kaj na hoye jay)."""
    now_bd = datetime.now(timezone.utc) + BD_OFFSET
    now_minutes = now_bd.hour * 60 + now_bd.minute
    today_str = now_bd.strftime("%Y-%m-%d")
    tolerance = config.get("tolerance_minutes", 15)

    for slot in config.get("run_times_bd", []):
        h, m = map(int, slot.split(":"))
        slot_minutes = h * 60 + m
        if abs(now_minutes - slot_minutes) <= tolerance:
            slot_key = f"{today_str} {slot}"
            if progress.get("last_run_slot") == slot_key:
                continue  # aajke ei slot e already kaj hoye geche
            progress["last_run_slot"] = slot_key
            return True
    return False


def load_tasks():
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {"completed_index": -1, "done": False, "results": {}}
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable pawa jayni. "
            "GitHub Secrets e set korun ba local e export korun."
        )
    return anthropic.Anthropic(api_key=api_key)


def call_step(client: anthropic.Anthropic, prompt: str):
    """Ekta step call kore. Rate limit e RETRY_WAIT_CAP_SECONDS porjonto wait kore
    retry kore. Er beshi lagle None return kore (mane: ei run e r hobe na, porer
    scheduled run e hobe)."""
    waited = 0
    while True:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in response.content if b.type == "text")
        except anthropic.RateLimitError as e:
            wait_time = getattr(e, "retry_after", None) or DEFAULT_WAIT_SECONDS
            if waited + wait_time > RETRY_WAIT_CAP_SECONDS:
                print(
                    f"Rate limit - wait time ({wait_time}s) cap ({RETRY_WAIT_CAP_SECONDS}s) "
                    "chariye jacche. Ei run bondho kore dicchi, progress save kora ache."
                )
                return None
            print(f"Rate limit. {wait_time}s wait kore retry korchi...")
            time.sleep(wait_time)
            waited += wait_time
        except anthropic.APIStatusError as e:
            print(f"API error: {e}. {DEFAULT_WAIT_SECONDS}s pore retry...")
            time.sleep(DEFAULT_WAIT_SECONDS)
            waited += DEFAULT_WAIT_SECONDS
            if waited > RETRY_WAIT_CAP_SECONDS:
                return None


def main():
    config = load_config()
    progress = load_progress()

    if progress.get("done"):
        print("Shob step already sesh hoye geche. Kichu korar nei.")
        return

    if not is_scheduled_time_now(config, progress):
        print("Ekhon apnar config.json e deya kono scheduled time na. Chup chap ber hoye jacchi.")
        return

    save_progress(progress)  # last_run_slot save kore rakhi, duibar na hoy

    client = get_client()
    tasks = load_tasks()

    start_index = progress["completed_index"] + 1
    print(f"Step {start_index + 1}/{len(tasks)} theke shuru korchi...")

    for i in range(start_index, len(tasks)):
        task = tasks[i]
        print(f"\n--- Step {i + 1}/{len(tasks)}: {task.get('id')} ---")

        result = call_step(client, task["prompt"])

        if result is None:
            # Ei run e r egono jabe na - progress joto hoyeche shoto save kore exit
            save_progress(progress)
            print("Run thamiye dicchi. Porer scheduled run theke continue hobe.")
            return

        progress["results"][str(task["id"])] = result
        progress["completed_index"] = i
        save_progress(progress)
        print(f"Step {i + 1} sesh. Progress save kora holo.")

    progress["done"] = True
    save_progress(progress)
    print("\nShob step sesh! Kaj complete.")


if __name__ == "__main__":
    main()

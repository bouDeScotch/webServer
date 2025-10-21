import requests
import time

URL = "https://test.boudescout.cc/random"
TOTAL = 100  # nombre max de tests
DELAY = 0.5  # délai entre les requêtes en secondes (ajuste selon ta bande passante)

success_count = 0
start_time = time.time()

for i in range(TOTAL):
    # ajouter un paramètre unique pour éviter le cache
    params = {"nocache": str(int(time.time() * 1000))}
    try:
        r = requests.get(URL, params=params, timeout=5)
        if r.status_code == 200:
            success_count += 1
            print(f"[{i + 1}/{TOTAL}] OK ({r.status_code})")
        else:
            print(f"[{i + 1}/{TOTAL}] Échec ({r.status_code})")
    except requests.RequestException as e:
        print(f"[{i + 1}/{TOTAL}] Exception: {e}")

    time.sleep(DELAY)

end_time = time.time()
print("\n=== Résultat ===")
print(f"Requêtes réussies : {success_count}/{TOTAL}")
print(f"Temps total : {end_time - start_time:.2f} secondes")
print(
    f"Requêtes par seconde approximatives : {success_count / (end_time - start_time):.2f}"
)

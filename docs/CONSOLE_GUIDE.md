# Live console guide

What every part of the live console (http://localhost:8099) does. All screenshots are from the running
system; the red numbers match the tables. Start the system first with `bash scripts/demo_up.sh`
(see [SETUP_AND_USAGE.md](SETUP_AND_USAGE.md)).

## 1. The page

![Console overview](console_guide/01_overview.png)

| # | Part | What it does | Türkçe |
|---|---|---|---|
| 1 | Header | Page title; names the components that are running. It is only a label. | Başlık, yalnızca bilgi |
| 2 | Clock | Current time (UTC), showing that the page is live. | Canlı saat |
| 3 | API documentation (Swagger) | The backend's API page, http://localhost:8000/docs. Sends real requests. See sections 5–7. | API isteklerini elle göndermek için |
| 4 | Buttons | Each one runs a command on this computer. See section 2. | Hazır senaryo düğmeleri |
| 5 | Terminal | Shows the command and its output, line by line. Scroll with the mouse wheel. | Komut ve çıktısı |
| 6 | Backend log | Live `docker logs` of our backend: every request and its HTTP status. | Backend'e gelen istekler |
| 7 | NEF log | Live `docker logs` of NEF-QoS: QoS requests sent to the Open5GS PCF and its answer. | 5G çekirdeğine giden QoS istekleri |

## 2. The buttons

![Buttons](console_guide/02_buttons.png)

| # | Button | Command | What happens | Reaches the 5G core? | Türkçe |
|---|---|---|---|---|---|
| 1 | Testbed | `demo_cli.py status` | Lists running containers, the APIs found in CAPIF, and the phones' IP addresses. No LLM call. | Only reads | Sistemin durumu |
| 2 | S1 dry run | `demo_cli.py run s1` | "Video-streaming quality for 30 minutes": plans and validates, sends nothing. | No | S1'i planlar, göndermez |
| 3 | S1 live | `demo_cli.py run s1 --live` | Closes that phone's old QoD session, then runs S1 through CAMARA QoD → NEF-QoS → PCF. | **Yes** | S1'i gerçekten çalıştırır |
| 4 | S2 live | `demo_cli.py run s2 --live` | Asks for a phone's location through CAMARA Location → NEF. The location data is emulated, and no PCF line appears. | NEF only | Konum sorgusu |
| 5 | S3 live | `demo_cli.py run s3 --live` | Vague request ("for a long time"). The LLM picks QoS Provisioning, the keyword planner picks QoD, so the call is **held**. | No | Belirsiz istek, onay bekler |
| 6 | S3 confirm | `demo_cli.py run s3 --live --confirm` | Same request sent with `confirm_service: true`. The LLM plans again, and the call goes directly to NEF-QoS → PCF. | **Yes** | Onaylayıp gönderir |
| 7 | Faults | `demo_cli.py faults --per-fault 1` | Breaks correct plans on purpose and shows which layer catches each fault (about 30 s). Provider calls are not made. | No | Bilerek hata ekler |
| 8 | Results | `demo_cli.py results` | Prints the 300-intent results from the stored files. | No | Kayıtlı sonuçlar |
| 9 | Clear | – | Empties the terminal pane only. Nothing is stopped, and the logs stay. | No | Terminali temizler |

## 3. Reading the terminal: Testbed

![Testbed output](console_guide/03_testbed_output.png)

| # | Output | Meaning | Türkçe |
|---|---|---|---|
| 1 | Command line | The command the button started. | Çalışan komut |
| 2 | Running containers | How many containers run per group. | Çalışan container sayıları |
| 3 | CAPIF discovery | Our backend is a CAPIF invoker and found 5 published APIs over mTLS. | CAPIF'in bulduğu API'ler |
| 4 | UE PDU sessions | The three simulated phones and the IPs the 5G core gave them. | Telefonlar ve IP'leri |

## 4. Reading the terminal and the logs: live calls

### S1 live

![S1 live output](console_guide/04_s1_live_output.png)

| # | Output | Meaning | Türkçe |
|---|---|---|---|
| 1 | REQUEST | The intent sent to `POST /orchestrate`; `dry_run: false` means live. The phone number is masked on screen. | Gönderilen istek |
| 2 | PLAN | Planner phase 1: the model and the service and operation it chose. | LLM'in seçtiği servis |
| 3 | payload | Planner phase 2: the JSON request the LLM wrote. | LLM'in yazdığı JSON |
| 4 | VALIDATION | Result of L1 (schema), L2 (telecom rules) and L3 (CAPIF registry). | Üç doğrulama katmanı |
| 5 | registry_checked | `true`: L3 really asked OpenCAPIF. | CAPIF'e gerçekten soruldu |
| 6 | CROSS-CHECK | The keyword planner's choice. `agrees` lets a live call continue. | İkinci planlayıcı aynı fikirde |
| 7 | EXECUTION | The CAMARA QoD provider answered HTTP 201. | Sağlayıcı kabul etti |
| 8 | UE IP, profile | Phone number resolved to the UE's IP from the subscriber database; streaming class mapped to the operator profile. | Numara → IP, profil eşleme |
| 9 | status | `AVAILABLE`: the QoD session is active. | Oturum aktif |
| 10 | TIMINGS | Time per stage. Planning is the LLM call. | Süreler |
| 11 | Backend log | The backend received the request and answered 200. | Backend isteği aldı |
| 12 | Created subscription | NEF-QoS received the AsSessionWithQoS request. | NEF isteği aldı |
| 13 | Forwarding … to PCF | NEF-QoS sends it to the Open5GS PCF. | NEF, PCF'ye iletiyor |
| 14 | Response status code: 201 | **The PCF accepted it: the request reached the 5G core.** | PCF kabul etti, asıl kanıt |
| 15 | PCF successfully allocated | NEF-QoS confirms the session. | Oturum ayrıldı |

### S3 live, then S3 confirm

![S3 output](console_guide/05_s3_output.png)

| # | Output | Meaning | Türkçe |
|---|---|---|---|
| 1 | PLAN | The LLM chose QoS Provisioning. The expected answer in our dataset is QoD. | LLM'in seçimi |
| 2 | VALIDATION | All layers pass: the plan is valid and the service is published. They cannot tell that it may be the wrong service. | Doğrulama bunu yakalayamaz |
| 3 | CROSS-CHECK | The keyword planner chose QoD, so the live call is held. | İki planlayıcı farklı, bekletildi |
| 4 | EXECUTION | Nothing was sent to the network. | Ağa gitmedi |
| 5 | `--confirm` | The second button: the operator confirms. | Operatör onayı |
| 6 | EXECUTION | NEF-QoS (port 8585) answered HTTP 201. Provisioning has no CAMARA provider in between. | NEF kabul etti |
| 7 | status | `ACTIVE`: the assignment is active in the core. | Atama aktif |
| 8 | NEF log | The PCF answered 201. | PCF kabul etti |

## 5. API page: the endpoints

Click a row to open it. GET rows read information; POST rows send or change something.

![Endpoints](console_guide/06_swagger_endpoints.png)

| # | Endpoint | What it does | Türkçe |
|---|---|---|---|
| 1 | `GET /health` | Is the backend running? | Backend açık mı |
| 2 | `GET /notifications` | Describes the callback receiver. | Bildirim alıcısı bilgisi |
| 3 | `POST /notifications` | Receives callbacks from CAPIF and the providers. You do not call it by hand. | Bildirimleri alır |
| 4 | `GET /config/provider` | Which LLM is active. | Aktif LLM |
| 5 | `POST /config/provider` | Switches the LLM: `{"provider": "openai"}`, `"anthropic"` or `"gemini"`. | LLM değiştirir |
| 6 | `POST /orchestrate` | **The main endpoint:** intent in, validated (and optionally executed) API call out. | Ana uç nokta |
| 7 | `GET /catalog/services` | The four CAMARA services and their operations. | Servis kataloğu |
| 8 | `GET /capif/status` | Connection to OpenCAPIF and certificates. | CAPIF bağlantısı |
| 9 | `GET /capif/invoker` | Our identity in CAPIF. | CAPIF kimliğimiz |
| 10 | `POST /capif/invokers/onboard` | Registers the backend in CAPIF. `start.sh` does this. | CAPIF'e kayıt |
| 11 | `GET /capif/discover` | The APIs published in CAPIF. | Yayımlanan API'ler |
| 12 | `POST /capif/publish` | Publishes one service in CAPIF. | Servis yayımlar |
| 13 | `POST /capif/publish/catalog` | Publishes the catalog in CAPIF. | Kataloğu yayımlar |

## 6. API page: sending a request

### Open the endpoint

![Try it out](console_guide/07_swagger_try_it_out.png)

| # | Part | What it does | Türkçe |
|---|---|---|---|
| 1 | Endpoint row | Opens and closes the endpoint. | Açar, kapatır |
| 2 | Try it out | Makes the request body editable. | Düzenlemeyi açar |

### Write the request

![Request](console_guide/08_swagger_request.png)

| # | Part | What it does | Türkçe |
|---|---|---|---|
| 1 | Cancel | Leaves edit mode. | Düzenlemeden çıkar |
| 2 | Reset | Restores the example body. | Örneğe döndürür |
| 3 | Request body | The request. `intent`: the sentence. `dry_run`: `true` sends nothing, `false` executes. `orchestration_mode`: `llm-assisted` or `deterministic`. | İstek metni |
| 4 | Execute | Sends the request to the backend. | Gönderir |

### Read the response

![Response](console_guide/09_swagger_response.png)

| # | Part | What it does | Türkçe |
|---|---|---|---|
| 1 | Execute | Sends again. | Yeniden gönderir |
| 2 | Clear | Removes the response from the page. Nothing changes in the system. | Yanıtı ekrandan siler |
| 3 | Curl | The same request as a terminal command. | Aynı isteğin komutu |
| 4 | Request URL | The address that was called. | Çağrılan adres |
| 5 | Code | HTTP status: 200 OK; 422 still invalid after three corrections; 502 LLM failed; 503 live call refused because CAPIF is unreachable. | HTTP sonucu |
| 6 | Response body | The result in JSON. See section 7. | Yanıtın kendisi |
| 7 | Download | Saves the response as a file. | Yanıtı indirir |
| 8 | Response headers | Technical HTTP headers. | HTTP başlıkları |
| 9 | Request duration | Total time seen by the browser. | Toplam süre |

The "Responses" section below these (Example Value, Schema) is fixed documentation, not your result.

## 7. API page: the response, field by field

Example: S1 with `dry_run: true`.

![Response fields](console_guide/10_swagger_response_fields.png)

| # | Field | Meaning | Türkçe |
|---|---|---|---|
| 1 | `intent` | The request as received. | Gelen istek |
| 2 | `mode` | Which planner produced the plan. | Hangi planlayıcı |
| 3 | `selected_service` | Catalog entry of the chosen service. | Seçilen servis |
| 4 | `steps` | The plan: operation, `payload` and the LLM's `rationale`. | Plan ve JSON |
| 5 | `validation` | Result and issues of L1, L2, L3, plus `registry_checked`. | Doğrulama sonucu |
| 6 | `execution_result` | What execution did: `dry-run`, `created`, `ok`, `held-for-confirmation` or `provider-error`. | Yürütme sonucu |
| 7 | `execution_results` | The same for every step (requests with several parts). | Tüm adımlar |
| 8 | `planner` | `model`, whether the CAPIF list was used, and the raw LLM outputs. | Model ve ham çıktı |
| 9 | `feedback` | Whether the LLM had to correct the plan, and the correction history. | Düzeltme döngüsü |
| 10 | `timings_ms` | Milliseconds per stage. | Süreler |
| 11 | `service_crosscheck` | The keyword planner's choice, `agrees`, and `held`. | Çapraz kontrol |

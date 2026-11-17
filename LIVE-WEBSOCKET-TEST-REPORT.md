# LIVE WEBSOCKET TEST REPORT — OKEY MUHABBET (`sistem.okeymuhabbet.com:4082`)

- **Tarih:** 2026-11-17 (`09:29:03 UTC`)
- **Hedef:** `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket`
- **Kanıt Dosyaları:** `live-test/reports/faz3_websocket_validation.json`, `live-test/reports/test_execution_ledger.json`

---

## 1. Yönetici Özeti ve Yetki Sınırı

Görev talimatının 4. bölümü uyarınca (*"Yetkili bir test ortamı veya üretim sunucusu için açık yazılı izin bulunmadıkça üretim WebSocket servisine uygulama protokolü seviyesinde bağlantı, kimlik doğrulama veya olay gönderimi yapma"*):

1. **Üretim `:4082` üzerinde yalnızca pasif TCP taşıma erişilebilirliği (`0` uygulama baytı) ölçülmüştür.** Üretim sunucusunda `HTTP 101 Upgrade` veya `EIO=4` oturumu başlatılmamıştır (`LIVE-WS-02-PROD-APP-GATE` -> **`ENGELLENDİ`**).
2. **RFC 6455 WebSocket `HTTP 101 Switching Protocols`, `Sec-WebSocket-Accept`, Engine.IO v4 `0{...}` açılış paketi, `2`/`3` Ping/Pong gecikmesi, zaman aşımı ve kopma sonrası yeniden bağlanma mekanizmaları** ikili koddan (`SocketIOPlus.dll` / `libil2cpp.so`) çıkarılan birebir kurallarla `LocalEngineIOWebSocketServer` (`LOCAL_MOCK`) üzerinde doğrulanmıştır.

| Test ID | Ortam | Kontrol | Sonuç | Durum Etiketi |
|---|---|---|---|---|
| `LIVE-WS-01-TCP4082` | `PRODUCTION_SAFE_READONLY` | `185.33.130.138:4082` TCP 3-yollu el sıkışma (`0` bayt veri) | Açık, `14.592 ms` | **`KANITLANDI`** |
| `LIVE-WS-02-PROD-APP-GATE` | `PRODUCTION_SAFE_READONLY` | Üretimde `HTTP 101` / `EIO=4` oturum açma | Yazılı izin yokluğunda durduruldu | **`ENGELLENDİ`** |
| `MOCK-WS-03-EIO4-HANDSHAKE-PING` | `LOCAL_MOCK` | `HTTP 101` + `Sec-WebSocket-Accept` + `EIO=4` `0{sid}` + `2`/`3` Ping/Pong | `HTTP 101`, `RTT = 0.459 ms` | **`KANITLANDI`** (Mock) |
| `MOCK-WS-04-RECONNECT` | `LOCAL_MOCK` | İlk bağlantı düşürüldüğünde artan gecikmeli yeniden bağlanma | 2. denemede bağlandı (`69.117 ms`) | **`KANITLANDI`** (Mock) |

---

## 2. Statik İkili Kod Bulguları (`SocketIOPlus.dll` & `SuWebRequest` — `KANITLANDI`)

Normal Ghidra `12.1.4` ve `level1` sahne serileştirmesi üzerinden doğrulanan kesin parametreler:

- **Sahne Yapılandırması (`level1+0x7879`):**
  - `serverUrl = "http://sistem.okeymuhabbet.com:4082"` (TLS/WSS kullanılmaz; düz TCP `:4082` üzerinden `ws://` yükseltmesi yapılır).
  - `volatileOperationMode = 1`
  - `maxConnectAttempts = 10`
  - `raisingReconnectDelay = 1` (her başarısız denemede bekleme süresini artıran doğrusal/kademeli geri çekilme).
- **Taşıma Katmanı Seçimi (`SocketIOPlus.EngineIO.Tranceiver::Connect @ RVA 0x01ACF57C`):**
  - HTTP long-polling devre dışıdır; istemci doğrudan `?EIO=4&transport=websocket` sorgusu ile RFC 6455 WebSocket bağlantısı kurar.
  - Varsayılan yol (`SocketIOClient::Awake @ RVA 0x01AC8848`): `"/socket.io/"`.
- **Android Ağ Güvenliği Uyumu (`GÜÇLÜ İPUCU`):** `:4082` kanalı şifresiz `ws://` (`http://` şeması) kullandığından, bağımsız bir Android istemcisinde `network_security_config.xml` içinde `sistem.okeymuhabbet.com` etki alanı için `cleartextTrafficPermitted="true"` tanımlanması zorunludur (Android 9+ varsayılan olarak açık metin trafiği engeller).

---

## 3. Canlı Taşıma Ölçümü (`PRODUCTION_SAFE_READONLY`)

- **Hedef Konak / Port:** `sistem.okeymuhabbet.com:4082` -> `185.33.130.138:4082`
- **DNS Süresi (Önbellekli):** `0.649 ms`
- **TCP El Sıkışma Süresi:** `14.592 ms`
- **Gönderilen Uygulama Baytı:** `0`
- **Değerlendirme:** `185.33.130.138` üzerindeki `4082` TCP portu genel İnternet erişimine açıktır ve düşük gecikmeyle yanıt vermektedir. Ancak **salt TCP portunun açık olması çalışan bir oyun oturumu kanıtı değildir**; üretim sunucusunun canlı `EIO=4` el sıkışma parametreleri (`pingInterval`, `pingTimeout`, `maxPayload`) yazılı yetki alınana kadar **`BİLİNMİYOR` / `ENGELLENDİ`** durumundadır.

---

## 4. Yerel Mock WebSocket ve Dayanıklılık Doğrulaması (`LOCAL_MOCK`)

`live-test/src/websocket/handshake.py` içindeki `WebSocketClient` ve `LocalEngineIOWebSocketServer` ile doğrulanan davranışlar:

1. **RFC 6455 El Sıkışma (`MOCK-WS-03-EIO4-HANDSHAKE-PING`):**
   - `GET /socket.io/?EIO=4&transport=websocket HTTP/1.1` isteğine `HTTP/1.1 101 Switching Protocols` yanıtı (`22.176 ms`) alındı.
   - `Sec-WebSocket-Accept` başlığının `base64(SHA1(Sec-WebSocket-Key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))` değeriyle birebir eşleştiği doğrulandı (`accept_valid = true`).
   - İstemci->Sunucu çerçevelerinde 4 baytlık RFC 6455 maskeleme zorunluluğu ve TCP akış birleşmesi (HTTP `101` başlığının hemen arkasından aynı TCP segmentinde gelen ilk `0{...}` çerçevesinin tamponda korunması) doğrulandı.
2. **Engine.IO v4 Açılış ve Ping/Pong:**
   - Sunucu bağlantı açılışında `0{"sid":"eio_mock_01","upgrades":[],"pingInterval":25000,"pingTimeout":20000}` paketini iletti.
   - Sunucu Engine.IO ping (`"2"`) gönderdiğinde istemci `"3"` (pong) ile yanıt verdi (`RTT = 0.459 ms`).
3. **Kopma ve Yeniden Bağlanma (`MOCK-WS-04-RECONNECT`):**
   - `drop_first_connection=True` senaryosunda sunucu ilk TCP bağlantısını `HTTP 101` öncesinde kapattı; istemci soket sızıntısı oluşturmadan (`0` `ResourceWarning`) `raisingReconnectDelay` mantığıyla 2. denemede bağlantıyı kurup `0{...}` açılış çerçevesini aldı (`69.117 ms`).

# Okey Muhabbet — Canlı Protokol Doğrulama ve Tekrarlanabilir Test Paketi (`live-test/`)

Bu dizin, `com.adnc.okeymuhabbet` (`v3.1.33`, `versionCode: 118`, Unity `6000.5.0f1` IL2CPP ARM64) istemci-sunucu protokolünün güvenli taşıma katmanı yoklamalarını, yerel mock doğrulamalarını ve oyun mantığı (`Akıllı Diz` / `Okey ile Bit`) simülasyonlarını içerir. Harici paket bağımlılığı yoktur; yalnızca standart Python 3.13 kütüphaneleri kullanılır.

## Güvenlik ve Yetki Sınırları

1. **Üretim HTTP (`https://sistem.okeymuhabbet.com/`):** Yalnızca kimlik doğrulamasız, parametresiz, salt okunur DNS / TCP 443 / TLS / `HEAD /` ve `GET /` kontrolleri çalıştırılır (`?h=` ve `?d=` gönderilmez). İmzalı komut zarfı testleri yerel `LocalMockHttpServer` üzerinde sentetik tuz (`SYNTHETIC_HTTP_16`) ile doğrulanır (`allow_non_local=False` varsayılan koruması aktiftir).
2. **Üretim WebSocket (`sistem.okeymuhabbet.com:4082`):** Açık yazılı izin bulunmadığından üretim `:4082` portuna yalnızca `0` uygulama baytı gönderen pasif TCP 3-yollu el sıkışma erişilebilirlik testi yapılır; RFC 6455 `HTTP 101`, `EIO=4`, Socket.IO v4 `CONNECT`/`EVENT`/`PING`/`PONG`/`DISCONNECT` ve yeniden bağlanma testleri yerel `LocalEngineIOWebSocketServer` ve `LocalOkeyProtocolMockStack` üzerinde çalıştırılır.
3. **Gizli Veri Maskeleme (`src/diagnostics/recorder.py`):** `token`, `token_id`, `session_id`, `_t`, `h`, `salt`, `secret`, `cookie`, `set-cookie`, `machash` alanları ve URL sorgu parametreleri diske yazılmadan önce otomatik olarak `"[REDACTED]"` değerine dönüştürülür.

## Dizin Yapısı

```text
live-test/
  src/
    diagnostics/
      recorder.py                 # Yapılandırılmış kanıt kaydı ve gizli veri maskeleme
      run_evidence_collection.py  # FAZ 2 - FAZ 5 kanıt üretim betiği
    http/
      probe.py                    # Güvenli üretim HTTP yoklaması, MD5 imzalama, DuplicateGuard ve HTTP mock
    websocket/
      handshake.py                # Pasif TCP :4082 yoklaması, RFC 6455 istemcisi, reconnect ve EIO=4 WS sunucusu
    socketio/
      parser.py                   # Engine.IO v4 + Socket.IO v4 (Protocol v5) kodlayıcı/çözücü ve çift kanallı mock
    protocol/
      schemas.py                  # 7 olay JSON şema doğrulayıcısı, Tas ayrıştırıcısı, Akıllı Diz ve Okey ile Bit motoru
  tests/                          # Birim ve entegrasyon testleri (unittest)
  fixtures/
    protocol_fixtures.json        # Statik analizle kanıtlanmış zarf ve olay şeması örnekleri
  reports/                        # Çalıştırma sonrası üretilen maskelenmiş JSON kanıt dosyaları
```

## Çalıştırma Komutları

### 1. Birim ve Protokol Testlerini Çalıştırma (Çevrimdışı / %100 Yerel)

```powershell
python -W default -m unittest discover -s live-test/tests -v
```

### 2. FAZ 2–FAZ 5 Kanıt Raporlarını Yeniden Üretme

```powershell
python live-test/src/diagnostics/run_evidence_collection.py
```

Üretilen kanıt dosyaları:
- `live-test/reports/faz2_live_http_probe.json`
- `live-test/reports/faz3_websocket_validation.json`
- `live-test/reports/faz4_5_protocol_and_engine.json`
- `live-test/reports/test_execution_ledger.json`

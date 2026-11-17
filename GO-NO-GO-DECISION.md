# GO / NO-GO KARAR BELGESİ VE EKSİK KANIT KAPATMA PLANI (`GO-NO-GO-DECISION.md`)

> **Proje:** Okey Muhabbet (`com.adnc.okeymuhabbet` `v3.1.33`) Alternatif Android İstemcisi Gerçeklik Testi  
> **Tarih:** 2026-11-17  
> **Karar Kuralı:** Gerçek sunucu kabulü canlı olarak kanıtlanmadan `GO` verilmez; statik bulgular canlı bağlantı kurulmuş gibi sunulmaz.

---

## 1. Altı Karar Sorusunun Kanıtlı Yanıtları

### Soru 1: Gerçek sunucu bağlantısı doğrulandı mı?
- **Yanıt:** **HAYIR (`ENGELLENDİ` — Yalnızca Statik Olarak `%100 KANITLANDI`).**
- **Kanıt:** Sunucu adresleri (`https://sistem.okeymuhabbet.com/` @ `level1+0x7DBC` ve `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket` @ `level1+0x7879` + `Tranceiver.Connect @ RVA 0x01ACF57C`), çerçeveleme ve JSON zarfları ikili koddan kesin olarak çıkarılmıştır. Ancak çalışma sınırları gereği üretim sunucusuna izinsiz bağlantı/istek yapılmamış; fiziksel cihazda (Xiaomi 17T Pro, root yok, `ro.debuggable=0`) ise PAIRIP sideload engeli ve Play Store sürümünün şifreli HTTPS (`sistem.okeymuhabbet.com`) trafiği harici düz metin yakalamaya kapalı olduğundan canlı paket alışverişi gözlemlenmemiştir.

### Soru 2: Misafir veya meşru kullanıcı oturumu bağımsız istemciden başlatılabiliyor mu?
- **Yanıt:** **Statik protokol düzeyinde `GÜÇLÜ İPUCU`, canlı sunucu kabulü açısından `BİLİNMİYOR` (`ENGELLENDİ`).**
- **Kanıt:**
  - **Misafir Girişi (`giris-misafir`):** `SuNetwork.MisafirGirisi` (`RVA 0x019B2B0C`) ve UI butonu (`resources.assets+0x70315C`) herhangi bir Play Integrity veya paket imzası gerektirmeden `token_id`, `device_id`, `machash` ve `_e: "giris-misafir"` alanlarını gönderir; `OnMisafirGirisi` (`RVA 0x019B2CE8`) dönen `id`, `kullanici`, `token_id`, `session_id` değerlerini kaydeder (`KANITLANDI`). Ancak sunucunun üretim ortamında yeni `giris-misafir` kayıtlarını açık tutup tutmadığı canlı test olmadan `BİLİNMİYOR`.
  - **Sosyal Girişler (`LoginGoogle` / `FacebookGiris`):** Google Play Games (`RVA 0x0197F168`) ve Facebook SDK (`RVA 0x0197E6BC`) sağlayıcı tarafında `com.adnc.okeymuhabbet` paket adını ve resmi geliştirici SHA-1 imzasını doğruladığından, geliştirici OAuth yapılandırması olmadan bağımsız bir APK'da doğrudan çalışmaz (`GÜÇLÜ İPUCU`).
  - **Mevcut `token_id` ile Giriş (`SuNetwork.Giris @ RVA 0x019B1940`):** `_e: "giris-GirisYap"` yalnızca `token_id` ve `machash` gönderir (`KANITLANDI`), ancak başka bir istemciden token kopyalamak çalışma sınırları ve güvenlik kuralları gereği kapsam dışıdır.

### Soru 3: Sunucu istemciyi paket adı, imza veya bütünlük kontrolüyle reddediyor mu?
- **Yanıt:** **İstemci ağ katmanında paket adı, APK sertifika imzası veya Play Integrity kontrolü YOKTUR (`KANITLANDI`); buna karşılık paylaşımlı sabit tuz imzası ve sürüm kontrolü VARDIR (`KANITLANDI`).**
- **Kanıt:**
  - DEX (`ev_bce20d9021b7e540...`), `ScriptingAssemblies.json` ve `libil2cpp.so` içinde Play Integrity, SafetyNet, Firebase App Check veya sertifika parmak izi gönderimi bulunmamaktadır (`KANITLANDI`).
  - Önceki raporlarda şüphelenilen `OyunMotoru.PackNameFinder` (`RVA 0x01997F3C`) hiçbir yerden çağrılmayan (`0 caller`) bir mağaza paket dizgi ayrıştırıcısıdır (`KANITLANDI`).
  - PAIRIP (`libpairipcore.so`) tamamen yerel bir APK açılış kilididir; oyun sunucusuna veri iletmez (`KANITLANDI`).
  - Sunucunun uyguladığı kanıtlanmış ağ kontrolleri şunlardır: (a) HTTPS GET `?h=` MD5 sabit tuz imzası (`<Send>d__27.MoveNext @ RVA 0x019C6374`, `lit#1429`), (b) Socket.IO `/` ad alanı el sıkışma dizgisi (`SuWebRequest.Callback @ RVA 0x019C5090`, `lit#399`), (c) `versiyonkontrol-versiyonkontrol` (`"Versiyon": "3.1.33"`, `"os": "ANDROID"` @ `RVA 0x019B0E70`). Sunucu önünde ek WAF / User-Agent / IP hız sınırı bulunup bulunmadığı ise `BİLİNMİYOR`.

### Soru 4: Oyun masası ve taş akışı bağımsız istemci tarafından yönetilebilir mi?
- **Yanıt:** **Protokol mimarisi açısından EVET (`KANITLANDI`), taş kimliği tel formatının canlı teyidi açısından `BİLİNMİYOR`.**
- **Kanıt:** Masa listesi (`MasaListesi`), masaya oturma (`MasayaOtur`), ıstaka güncelleme (`OnIstakayiGuncelle @ RVA 0x019B94AC`), taş çekme (`TasCek @ RVA 0x019B8DD0`), taş atma (`TasAt @ RVA 0x019B8B6C`), çifte gitme (`CifteGit @ RVA 0x019C1D4C`) ve el bitirme (`OyunBitirBeta @ RVA 0x019B7BEC`) tamamen standart JSON mesajlarıyla yürütülmektedir. Oyun kuralları ve deste sunucu otoritelidir.

### Soru 5: Akıllı Diz ve Okey ile Bit özellikleri protokol açısından uygulanabilir mi?
- **Yanıt:** **EVET (`KANITLANDI`).**
- **Kanıt:**
  - **Akıllı Diz:** Oyuncu tur boyunca ıstakasındaki 28 yuvayı yerel olarak yönetir (`MasaPerHesaplayici @ RVA 0x01A09D98..0x01A0D280` halihazırda istemcide seri/renk perlerini, çiftleri ve kalan taş toplamını yerel olarak hesaplamaktadır). Üstelik sunucuda `masaseridiz-perdiz` (`RVA 0x019B8A50`) komutu da mevcuttur. Istaka dizilimi yalnızca el bitirilirken sunucuya gönderilir.
  - **Okey ile Bit:** Oyun bitirme komutu (`masaoyunbitir-oyunbitirbeta` @ `RVA 0x019B7BEC`) 28 yuvalık `'-'` ve `'Bos'` ayrımlı ıstaka dizilimini (`"taslar"`) ve atılan 15. taşı (`"bitentas"`) sunucuya gönderir (`Masa.OyunBitir @ RVA 0x019FF938`). Oyuncunun elindeki 14 taş geçerli per/çift oluşturduğunda ve 15. taş aktif Okey taşı (`OkeyTas`) olduğunda, Okey taşını `"bitentas"` olarak göndermek protokol düzeyinde doğrudan "Okey ile Bit" işlemini gerçekleştirir (`KANITLANDI`).

### Soru 6: Geliştirme aşamasına geçmek için yeterli teknik kanıt var mı?
- **Yanıt:** **Tam Android istemci geliştirmeye doğrudan başlamak için HAYIR (`GO` verilemez); kontrollü canlı doğrulama fazına geçmek için protokol bilgisi TAMDIR.**
- **Kanıt:** Statik tersine mühendislik ile istemci-sunucu protokolünün %100'ü çözülmüştür; ancak (1) sunucu sahibinden yetki/izin, (2) `giris-misafir` komutunun canlı sunucuda kabul edildiğinin kanıtı ve (3) canlı `IstakayiGuncelle` / `TasCek` taş kimliği dizgi örnekleri doğrulanmadan uygulama kodlamasına geçilmesi mühendislik ve uyumluluk açısından hatalıdır.

---

## 2. NİHAİ KARAR: `CONDITIONAL GO` (Koşullu Geçiş — Canlı Doğrulama ve Yetkilendirme Şartıyla)

> **Seçilen Karar:** **`CONDITIONAL GO`** *(Gerçek sunucu kabulü henüz canlı test edilmediği için kesinlikle `GO` değildir; ancak statik analizde Play Integrity, mTLS veya sunucu taraflı APK imza doğrulaması gibi teknik bir engel bulunmadığı kanıtlandığından `NO-GO` da değildir.)*

### Neden `GO` Verilmedi?
1. Üretim sunucusuna izinsiz istek göndermeme kuralı gereği `https://sistem.okeymuhabbet.com/` ve `ws://sistem.okeymuhabbet.com:4082` uç noktalarına gerçek bağlantı kurulmamış, sunucu kabulü canlı olarak kanıtlanmamıştır (`ENGELLENDİ`).
2. HTTPS isteklerindeki sabit tuz (`lit#1429`) ve Socket.IO el sıkışma dizgisi (`lit#399`) uygulamaya özgü paylaşımlı sabitler olduğundan, geliştirici/sunucu sahibi (ADNC / Manc Games) onayı olmadan üçüncü taraf bir istemcide kullanılması kullanım koşullarına (ToS) aykırıdır.
3. `giris-misafir` akışının üretim sunucusunda hala açık olup olmadığı ve taş kimliklerinin (`TasAdi` / `OkeyTas`) birebir çalışma zamanı örneği henüz canlı gözlemle doğrulanmamıştır (`BİLİNMİYOR`).

---

## 3. Eksik Kanıtları Kapatacak Somut Teknik Doğrulama Planı (Uygulama Kodlaması Öncesi)

Tam Android istemcisi geliştirmeye başlamadan önce aşağıdaki **4 adımlı, minimum kapsamlı yetkili doğrulama planı** uygulanmalıdır:

### Adım 1 — Geliştirici / Ortam Yetkilendirmesi (Ön Koşul)
- Sunucu sahibinden (`com.adnc.okeymuhabbet` / Manc Games) test ortamı veya yazılı protokol uyumluluk izni alınması (veya test için yetkili bir geliştirici/staging uç noktasının tahsis edilmesi).

### Adım 2 — Tek İsteklik Yetkili Oturum ve El Sıkışma Doğrulaması (`giris-misafir` + WS `:4082`)
- Yetkili test ortamında tek bir kontrol betiği ile:
  1. `GET /?h=<md5>&d={"token_id":"","device_id":"<test_id>","machash":"<md5>","_e":"giris-misafir"}` isteğine sunucunun `{"s":[{"i":"MisafirGirisi","d":{"id":...,"session_id":...}}]}` yanıtı verip vermediğinin doğrulanması.
  2. Alınan `id` ve `session_id` ile `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket` adresine bağlanılıp `40{"sid":"..."}` onayının ve `'VersiyonKontrol'` olayının alındığının doğrulanması.
  - **Karar Kapısı:** Eğer sunucu `giris-misafir` isteğini reddediyor ve sosyal OAuth zorunlu tutuyorsa, resmi geliştirici OAuth istemci kaydı olmadan proje otomatik olarak **`NO-GO`** durumuna geçer.

### Adım 3 — Taş Kimliği (Tile ID) ve `IstakayiGuncelle` Tel Formatının Kaydedilmesi
- Yetkili tek bir test masasında `OnMasayaGir` (`OkeyTas`), `OnIstakayiGuncelle` (`t`) ve `OnTasCek` (`tas`) olaylarının ham `"d"` JSON yükleri kaydedilerek:
  - Normal taşların (`1..52`, `54..105`), sahte okeylerin (`53`, `106` — `MasaPerHesaplayici.IsOkeyTile @ RVA 0x01A0A210`) ve aktif okey işaretlemesinin (`o`) birebir dizgi temsili kesinleştirilir.
  - `Masa.OyunBitir` (`RVA 0x019FF938`) tarafından üretilen 28 yuvalık `"-<Slot1>-...-<Slot28>"` dizgisinin başlangıç ayracı (`"-"`) sunucu kabul testiyle doğrulanır.

### Adım 4 — Bağımsız İstemci Prototipine Geçiş Kriteri
- Yalnızca Adım 1–3 başarıyla tamamlanıp tüm `BİLİNMİYOR` / `ENGELLENDİ` maddeleri `KANITLANDI` statüsüne geçtiğinde karar `GO` olarak güncellenir ve `Akıllı Diz` + `Okey ile Bit` modüllerini içeren Android istemci mimarisi kodlanmaya başlanır.

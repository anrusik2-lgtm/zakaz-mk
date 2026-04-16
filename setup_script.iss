[Setup]
; Основная информация
AppName=Заказ МК
AppVersion=14.04.2026
AppPublisher=AnRusik
AppPublisherURL=mailto:3380517@mail.ru
AppSupportURL=mailto:3380517@mail.ru
AppUpdatesURL=mailto:3380517@mail.ru

; Выходной файл установщика
OutputDir=installer
OutputBaseFilename=ZakazMK_Setup

; Установка в AppData\Local (папка пользователя)
DefaultDirName={localappdata}\ZakazMK
DefaultGroupName=Заказ МК

; Права администратора НЕ требуются
PrivilegesRequired=lowest

; Иконки
UninstallDisplayIcon={app}\ZakazMK.exe
SetupIconFile=C:\Users\oas\Desktop\База МК\1\icon.ico

; Сжатие
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern

; Разрешаем запись в реестр (для деинсталлятора)
[Registry]
Root: HKCU; Subkey: "Software\ZakazMK"; Flags: uninsdeletekey

; Язык
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

; Задачи
[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"

; ========== ФАЙЛЫ ==========
[Files]
; ============================================
; 1. ПРОГРАММНЫЕ ФАЙЛЫ (из папки dist)
; ============================================
Source: "dist\ZakazMK\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ============================================
; 2. ФАЙЛЫ ДАННЫХ (НЕ ПЕРЕЗАПИСЫВАТЬ!)
; Берутся из текущей установки, если есть — сохраняются
; ============================================
; ✅ Базы данных — только если НЕТ в AppData (сохраняем данные пользователя)
Source: "C:\Users\oas\AppData\Local\ZakazMK\database.db"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "C:\Users\oas\AppData\Local\ZakazMK\inventory.db"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "C:\Users\oas\AppData\Local\ZakazMK\orders.db"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; ============================================
; 3. РЕСУРСЫ (из папки проекта)
; ============================================
; ✅ Иконки и изображения — ВСЕГДА обновляем
Source: "C:\Users\oas\Desktop\База МК\1\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\oas\Desktop\База МК\1\image.png"; DestDir: "{app}"; Flags: ignoreversion

; ✅ Чертежи — только новые файлы, старые не трогаем
Source: "C:\Users\oas\Desktop\База МК\1\Чертежи\*"; DestDir: "{app}\Чертежи"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

; ============================================
; 4. КОНФИГ — СБРАСЫВАЕМ НАСТРОЙКИ, НО НЕ ЛИЦЕНЗИЮ!
; ============================================
; ✅ config.json — перезаписываем (сброс настроек окна), 
; но лицензия хранится в реестре и НЕ сбрасывается
Source: "C:\Users\oas\Desktop\База МК\1\config.json"; DestDir: "{app}"; Flags: ignoreversion

; ========== ЯРЛЫКИ ==========
[Icons]
Name: "{group}\Заказ МК"; Filename: "{app}\ZakazMK.exe"
Name: "{group}\Чертежи"; Filename: "{app}\Чертежи"
Name: "{group}\Удалить Заказ МК"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Заказ МК"; Filename: "{app}\ZakazMK.exe"; Tasks: desktopicon

; Запуск после установки
[Run]
Filename: "{app}\ZakazMK.exe"; Description: "Запустить Заказ МК"; Flags: postinstall nowait skipifsilent

; Удаление
[UninstallDelete]
Type: filesandordirs; Name: "{app}"; Check: IsUninstallDeleteAll

; ========== КОД ==========
[Code]
// Спрашиваем при удалении, точно ли юзер хочет удалить программу
function IsUninstallDeleteAll(): Boolean;
begin
  Result := MsgBox('Удалить программу "Заказ МК"?', 
                   mbConfirmation, MB_YESNO) = IDYES;
end;

// ✅ ПОДГОТОВКА К УСТАНОВКЕ: Очищаем только config.json, лицензию СОХРАНЯЕМ
function InitializeSetup(): Boolean;
var
  ConfigPath: String;
begin
  // 1. Удаляем config.json из AppData (сброс настроек окна, геометрии и т.д.)
  // ✅ Лицензия НЕ сбрасывается — она хранится в реестре (HKCU\Software\ZakazMK)!
  ConfigPath := ExpandConstant('{localappdata}\ZakazMK\config.json');
  if FileExists(ConfigPath) then
  begin
    Log('🗑️ Удаляю старый config.json: ' + ConfigPath);
    DeleteFile(ConfigPath);
  end;
  
  // 2. ✅ ЛИЦЕНЗИЮ В РЕЕСТРЕ НЕ ТРОГАЕМ!
  // Ключи license_activated, license_key, activated_at остаются нетронутыми
  // Программа при загрузке прочитает их из реестра → лицензия сохранится
  
  // 3. first_run тоже не трогаем — демо-период не сбрасывается
  // (если лицензия активна — это не важно, если нет — пользователь сам решит)
  
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('✅ Установка завершена. Путь: ' + ExpandConstant('{app}'));
    Log('📁 Базы данных сохранены (database.db, inventory.db, orders.db)');
    Log('🔑 Лицензия сохранена (ключи в реестре не тронуты)');
    Log('🎨 Ресурсы обновлены (иконки, чертежи)');
    Log('⚙️ Настройки окна сброшены (config.json перезаписан)');
  end;
end;
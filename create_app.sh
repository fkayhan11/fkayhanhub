#!/bin/bash
cat << 'APPLESCRIPT' > /Users/furkanmacbook/Desktop/Excel/converter.applescript
on open dropped_items
    repeat with item_ in dropped_items
        set posix_path to POSIX path of item_
        do shell script "/usr/bin/env python3 '/Users/furkanmacbook/Desktop/Excel/excel_client.py' " & quoted form of posix_path
    end repeat
    display notification "Dönüştürme başarıyla tamamlandı!" with title "Excel'e Çevirici"
end open

on run
    display dialog "Lütfen dönüştürmek istediğiniz ekran görüntüsünü bu uygulamanın simgesinin üzerine sürükleyip bırakın." buttons {"Tamam"} default button "Tamam"
end run
APPLESCRIPT

osacompile -o /Users/furkanmacbook/Desktop/Excel_Cevirici.app /Users/furkanmacbook/Desktop/Excel/converter.applescript
rm /Users/furkanmacbook/Desktop/Excel/converter.applescript

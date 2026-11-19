# Lua в HvH

**English:** [lua-api.en.md](lua-api.en.md)

Вкладка Config: конфиги и их экспорт слева, Lua справа. Вставь исходник, задай имя и нажми **Load / reload** (исходник больше ~195 KiB вставляется частями через **Add as part**). **Save source** сохраняет исходник в личном профиле; выбор сохранённого скрипта открывает его в редакторе. Запуск всегда ручной. **Unload** удаляет обработчики, рисунки и контролы, снимает изменения AA/Rage. **Delete saved** удаляет сохранённый исходник и выгружает этот скрипт. Сохранение исходника не сохраняет значения его контролов.

Начни с [быстрого старта](lua-guide.md). Готовые стартовые скрипты: `lua-examples/starter-hud.lua` (по одному элементу: FPS/график/фигуры) и `starter-hitlog.lua` (реальные свои результаты и опциональные 3D-трейсеры). Остальные примеры: `visuals.lua`, `aa-builder.lua`, `resolver.lua`, `images.lua`. Расширенные: `extended-visuals.lua` (панель с drag, clipping и графикой, включена сразу), `aa-builder-extended.lua` (пять состояний; включается чекбоксом). Готовые gamesense Lua не совместимы автоматически: здесь собственный API без FFI и игровых DLL.

## События

`client.set_event_callback(name, function)` / `client.unset_event_callback(name, function)`.

| Имя | Аргумент и поведение |
| --- | --- |
| `paint` | Один вызов на кадр. Рисунки этого кадра заменяют предыдущие. |
| `paint_ui` | После `paint`, тот же canvas и общий бюджет, также в меню/лобби. |
| `net_update_end` | `{tick}` после обработки публичного snapshot. Между кадрами сохраняется последний snapshot, без очереди устаревших пакетов. |
| `match_update` | Копия последнего публичного состояния матча; несколько обновлений за кадр объединяются. |
| `round_start`, `round_end` | Публичное состояние при переходе в freeze / ended. |
| `aim_fire` | Предсказанный выстрел rage: `{cmdNumber,target,damage,hitchance,pitch,yaw,backtrack,tick,foot,fake,health,custom}` (`tick` — запись цели, `foot` — корпус, в который целились, `fake` — цель чокает, `custom` — гипотеза от Lua `resolve`). Результат сервера приходит отдельным `shot`. |
| `setup_command` | Изменяемая копия команды до rage/AA. Доступна запись `forwardmove`, `sidemove` (-127…127) и `buttons` (маска из таблицы `buttons`). Номер команды и сетевое время защищены. Во время открытого меню не вызывается. |
| `anti_aim` | Команда после встроенного AA. Запись `yaw`, `pitch` (-89…89), `choke`, `send_packet`, `desync_amount` (0…58), `desync_side` (-1/1). Пакет — максимум 16 команд (15 зачоканных + отправленная, как sv_maxusrcmdprocessticks 16): дальше `choke`/`send_packet=false` не держат, сервер длиннее исполняет только сдвиг DT / фейкдак. `view_yaw`, `view_pitch`, `packet`, `chokedcommands` дают контекст; только чтение: `public_foot`, `public_lby`, `public_max_desync` (публичный корпус, который видят другие: шаг AnimState на каждый отправленный пакет), `real_foot`, `lby`, `max_desync` (реальный), `eye` (Vector3 hu), `fakelag_send` (решение фейклага: true отправить, false чокнуть, nil — фейклаг не решает). `bomb_action` (`'plant'`/`'defuse'` во время реальной установки/разминирования, иначе nil), `legit_aa` (зажат Legit anti-aim: встроенные pitch/yaw остались на взгляде). Движение исправляется автоматически. На лестнице, при блокировке и при прицельном выстреле rage не вызывается. Во время установки/разминирования вызывается только при включённом AA > Other «Anti-aim on bomb actions» (игрок заморожен, углы и десинк работают; фейклаг на это время сам встаёт на паузу). Обычный выстрел также возвращает исходные углы. DT/FD и ограничение длины пакета имеют приоритет над ручным send/choke. |
| `resolve` | `{slot,yaw,foot_yaw,max_desync,tick,sample}`. Верни абсолютный предполагаемый угол корпуса, таблицу `{foot=угол, confident=true/false}` или `nil` для встроенного алгоритма. `confident` решает за встроенный резольвер, «уверен» ли он в цели (Prefer safe point if unresolved). Работает при построении позы для rage, включая интерполяцию записей. Повторные запросы одинаковой позы в одной команде кешируются. |
| `shot` | Копия публичного события `Net.UnpackShot`: в том числе `shooter`, `cmdNumber`, `damage`, `start`, `impact`, `flags`. |
| `shutdown` | Выгрузка скрипта. После фатальной ошибки обработчик не вызывается. |

Обработчики идут в порядке загрузки скриптов. Для конфликтующих команд/гипотез выигрывает последний допустимый результат. Встроенные модели резольвера не обучаются на выстрелах при применённой пользовательской гипотезе `resolve`; реальных серверных углов API не раскрывает. Пример резольвера демонстрирует гипотезы, его точность не проверена.

## Меню и настройки

Каждый конструктор возвращает числовой handle, принадлежащий текущему скрипту:

```lua
local on = ui.new_checkbox('Enabled')
local yaw = ui.new_slider('Yaw', -180, 180, 180)
local mode = ui.new_combobox('Mode', {'One', 'Two'})
local tint = ui.new_color_picker('Color', 160, 200, 80, 255)
local enabled = ui.get(on)
ui.set(on, true)
local r,g,b,a = ui.get(tint)
```

Комбобоксы используют индексы с 1. Контролы появляются под кнопками Lua, доступны прокруткой.

Дополнительные контролы:

```lua
local list = ui.new_multiselect('Elements', {'Text', 'Arc'})
ui.set(list, {true, false}) -- boolean array; ui.get returns a copy
local text = ui.new_textbox('Caption', 'hello') -- max 256 bytes
local label = ui.new_label('Status')
ui.set(label, 'Updated')
local button = ui.new_button('Reset', function() client.log('reset') end)
local bind = ui.new_hotkey('Hotkey', 'K', 'Hold')
local active = ui.get(bind) -- boolean; Hold / Toggle / Always / OffHotkey
ui.set(bind, 'L', 'Toggle')
ui.set(tint, 255, 100, 80, 128) -- RGBA picker
ui.set_visible(list, false)
ui.set_callback(on, function(handle) client.log(ui.name(handle), ui.get(handle)) end)
```

Callbacks, buttons and timers execute on the next render dispatch, outside native input handlers; at most16 callbacks/frame/script, queue64. Excess notifications may be dropped. Hidden hotkeys remain active. Unload removes hotkeys, callbacks, controls and timers. `ui.is_menu_open()` returns a boolean; `ui.menu_position()` returns screen x,y.

`ui.get_setting('AA.yawOffset')` returns a copy. `ui.list_settings('AA.')` lists created controls. `ui.reference(key)` returns a script handle for an existing setting: `ui.get`, `ui.set`, `ui.set_callback` work on it, but hiding original controls is not supported. Writes are allowed for AA/Rage/Visuals/World/Misc, not Admin/Config/Players. Numbers validate against the actual slider/combo range; arrays must match the control's boolean options, colors accept `{r,g,b,a}` or a copied `{Color,Alpha}`, hotkeys accept `{Key='K',Mode='Hold'}`. Open the relevant menu section before referencing a conditional control that has not been created yet.

### Своя вкладка вместо встроенной

```lua
ui.override_tab('AA')                 -- AA / Rage / Visuals / World / Misc / Players / Skins
local on = ui.new_checkbox('Enabled')
ui.set_group(on, 'Builder')           -- groupbox title (1..40 chars); default = script name
local yaw = ui.new_slider('Yaw', -180, 180, 0)
ui.set_group(yaw, 'Angles')
```

Пока скрипт загружен, встроенные группы вкладки скрыты, а контролы скрипта стоят на их месте в своих группах (две колонки, порядок групп = порядок первого контрола). Встроенные настройки не сбрасываются и продолжают работать — меняется только интерфейс; вместе с `anti_aim`/`ui.set_setting` скрипт может полностью заменить AA. Unload/ошибка загрузки/`ui.restore_tab('AA')` возвращают вкладку. Одну вкладку держит один скрипт (`ui.is_tab_overridden(tab)`), Config/Cloud/Admin не заменяются. `ui.set_group(id, group, tab)` привязывает контрол к конкретной вкладке, если скрипт заменяет несколько; контролы без вкладки идут в первую заменённую. gamesense-путь `ui.new_*('AA', 'Anti-aimbot angles', 'Name')` сразу задаёт вкладку и группу. Контролы, не попавшие в заменённую вкладку, остаются в Config > Lua.

`ui.reset_setting(key)` releases this script's override. Unload restores the previous script owner or user's base value; user changes observed between calls become the new base. For a standalone AA builder use `anti_aim` command fields. `AA.desync`, `AA.desyncAmount`, `AA.yawModifier`, `AA.modifierRange` also expose the built-in mechanisms.

## Рисование

Координаты экрана в пикселях, цвета RGBA 0…255; alpha 255 — непрозрачный. Только внутри `paint`:

```lua
renderer.text(x,y,r,g,b,a,text,size) -- шрифт Code, size 8…48
renderer.rectangle(x,y,w,h,r,g,b,a)
renderer.line(x1,y1,x2,y2,r,g,b,a,thickness)
renderer.circle(x,y,radius,r,g,b,a,filled)
renderer.gradient(x,y,w,h,r,g,b,a,r2,g2,b2,a2,horizontal)
local x,y = renderer.world_to_screen(worldX,worldY,worldZ)
```

World-to-screen принимает Source hu, 12 hu = 1 stud. Возвращает nil вне экрана. Используются переиспользуемые GUI-объекты; слои ниже меню. Пул раздельный по Frame/TextLabel/ImageLabel: изменение числа линий не пересоздаёт последующие текст и картинки. Кеш держит максимум384 объекта каждого из этих трёх классов (1152 суммарно), но лимит активных рисунков остаётся384 на кадр. Неиспользуемые элементы скрываются; unload/error удаляет кеш. Можно сочетать примитивы для обводок, теней, свечения, индикаторов и анимаций.

Дополнительная графика:

```lua
renderer.rounded_rectangle(x,y,w,h,r,g,b,a,radius,corners) -- corners: 'left', 'tr', 'top', 'tl bl'... (остальные углы прямые)
renderer.rounded_outline(x,y,w,h,r,g,b,a,radius,thickness) -- обводка внутри прямоугольника, как ImGui AddRect
renderer.rectangle_outline(x,y,w,h,r,g,b,a,thickness)
renderer.triangle(x1,y1,x2,y2,x3,y3,r,g,b,a,filled,thickness) -- filled defaults true
renderer.polyline({{x1,y1},{x2,y2},{x3,y3}},r,g,b,a,thickness,closed)
renderer.arc(x,y,radius,startDegrees,sweepDegrees,r,g,b,a,thickness,segments)
local w,h = renderer.measure_text('hello',16,'ui_bold')
renderer.text_ex(x,y,'hello',{size=16,font='ui_bold',align='center',outline=true,
    rotation=0,color={255,255,255,255}})
renderer.world_line(vector.new(x1,y1,z1),vector.new(x2,y2,z2),r,g,b,a,thickness)
renderer.push_clip(x,y,w,h)
-- all draw functions still use absolute screen coordinates here
renderer.pop_clip()
```

Fonts: `code`, `ui`, `ui_bold`, `gotham`. Align: left/center/right. Polyline up to64 points, arc up to64 segments, clip nesting8 /16 clips per frame. Every generated primitive counts against384 draws. Filled triangles use two pooled right-triangle images and lazily allocate two64x64 masks (32KiB), counted in the script texture quota and freed on unload. Ordinary label updates change text directly, without rebuilding the entire Lua menu.

## 3D bullet tracers

`renderer.tracer(fromVector, toVector, options?)` creates a real client-side Roblox Beam and returns a private numeric handle. Call once in `shot`, not every `paint`. Endpoints and widths use Source hu (12 hu = 1 stud). The beam stays in world space and uses normal engine depth testing against opaque geometry; it does not draw through walls. No Instances are exposed and effects never affect collision, ray queries or server simulation.

```lua
local id = renderer.tracer(e.start, e.impact, {
    color={125,209,255,255}, width=2, end_width=.5,
    life=1, fade=.3, glow=1,
    texture='', texture_speed=0, texture_length=12,
})
renderer.remove_tracer(id) -- true if removed, false if already expired
renderer.clear_tracers() -- this script only
```

Options: RGBA color; start/end widths .05..24 hu; life .05..10 seconds; fade is the final 0..life seconds; glow 0..1 is Beam.LightEmission (not a bloom guarantee). Optional texture accepts an `rbxassetid://` image ID available to this experience, not an embedded PNG handle or HTTP URL; texture speed -20..20, texture length .1..256 hu. Asset permissions still apply. Defaults: warm white, width1 hu, life1s, fade.3s, glow.5, no texture. Straight camera-facing ribbon, not a cylindrical mesh. Maximum length16384 hu, 64 simultaneous /16 new tracers per script per rendered frame. Expiry, unload, reload and script errors remove effects. Ready-to-run example: `lua-examples/bullet-tracers.lua` (own confirmed shots by default; optional other players).

`through_walls=true` рисует трейсер поверх карты: простая линия постоянной толщины, `width` тогда в пикселях (1..10), без текстуры/свечения/`end_width`. У `renderer.effect` та же опция работает для `sphere`, `box` (плоский цвет без материала) и `text`.

## Картинки внутри Lua

PNG можно вставить прямо в исходник как строку `"\x89\x50\x4E..."` или Base64. Загрузка — только при инициализации скрипта, до событий; внутри `paint` рисуется уже готовая текстура:

```lua
local image = renderer.load_png_base64('...Base64 PNG...')
client.set_event_callback('paint', function()
    renderer.texture(image, 20, 20, 128, 128, 255, 255, 255, 255)
end)
```

| Функция | Данные |
| --- | --- |
| `renderer.load_png(bytes)` | Бинарная строка PNG, в том числе `\xNN`-литерал. |
| `renderer.load_png_base64(text)` | Стандартный Base64; допускает пробелы/переносы и префикс `data:image/png;base64,`. |
| `renderer.load_rgba(bytes,w,h)` | Бинарная строка ровно `w*h*4` байт, порядок RGBA, строки сверху вниз. |
| `renderer.load_rgba_base64(text,w,h)` | Те же RGBA-пиксели в Base64. |
| `renderer.texture(id,x,y,w,h,r,g,b,a[,sx,sy,sw,sh])` | Отрисовка с масштабированием, цветовым множителем и общей alpha. Белый цвет сохраняет исходные цвета. Необязательные `sx,sy,sw,sh` — нарисовать только этот прямоугольник текстуры (атласы, спрайт-листы). |
| `renderer.texture_size(id)` | Исходные `width,height`. |
| `renderer.free_texture(id)` | Освобождает картинку и её квоту; использовать этот handle дальше нельзя. |

Загрузчики возвращают числовой handle, приватный для текущего скрипта. Поддерживаются PNG с 8-битными каналами: RGB, RGBA, grayscale, grayscale+alpha; палитры 1/2/4/8 бит, `tRNS`, все пять фильтров, stored/fixed/dynamic DEFLATE. PNG CRC и zlib Adler проверяются. Interlaced/16-bit PNG нужно экспортировать как обычный non-interlaced 8-bit PNG; JPEG/SVG пока не поддерживаются. Необязательные размеры `load_png(bytes,w,h)` должны совпадать с PNG; масштабирование задаётся в `texture`.

Лимиты: исходная картинка до **1024×1024**, бинарный PNG до **512 KiB**, до **32 текстур / 1 MiB RGBA-пикселей на скрипт**. Один декодер ограничен примерно 200 ms; общий бюджет успешной загрузки картинок — 500 ms, после исчерпания следующая загрузка отклоняется. Это отдельная одноразовая работа при запуске, она не расходует 10 ms бюджета обычного кадра. Roblox также имеет собственный общий лимит памяти EditableImage; при его исчерпании скрипт получает понятную ошибку и выгружается. `Unload`, reload и ошибка автоматически освобождают все текстуры.

Готовый пример с PNG и прозрачными RGBA-пикселями: `lua-examples/images.lua`. Встроенная Base64/байтовая строка вместе с кодом для сохранения должна помещаться в 192 KiB исходника (запуск — до 2 MiB); большая картинка может потребовать меньшего разрешения или более компактного PNG. PNG не загружается на сайт Roblox и не требует HTTP; другие игроки эту локальную картинку не получают.

## Свои шрифты

Любой шрифт `.ttf` / `.otf` превращается в Lua-блок (PNG-атлас в Base64 + таблица глифов) утилитой из набора:

```
python tools/lua_font_pack.py MyFont.ttf 14 myfont.lua --name MYFONT [--chars ascii,cyrillic] [--merge icons.ttf 13 f000-f2ff]
```

Блок вставляется в скрипт как есть, дальше:

```lua
local tex = renderer.load_png_base64(MYFONT_PNG)
local font = renderer.load_font(tex, MYFONT_GLYPHS, {height = MYFONT_HEIGHT})
client.set_event_callback('paint', function()
    local w = renderer.font_text(font, 20, 20, 'Привет', 255, 255, 255, 255) -- возвращает ширину
end)
local w, h = renderer.font_measure(font, 'text')
```

`glyphs[кодовая точка] = {x, y, w, h, offset_x, offset_y, advance}`: прямоугольник глифа в атласе, где его левый верх стоит относительно пера (левый край, верх строки) и насколько сдвигается перо. `opts.height` — высота строки, `opts.fallback` — код глифа для отсутствующих символов (по умолчанию `?`). Один вызов `font_text` = один рисунок из 384, сколько бы ни было букв; неизменный текст не перестраивается. Координаты округляются до пикселя (глифы пиксельные). До 16 шрифтов и 4096 глифов в шрифте на скрипт, 4096 объектов-глифов всего. `--merge` вклеивает иконочный шрифт (Font Awesome и т.п.) в тот же атлас, как MergeMode в ImGui.

## Ввод текста и аватар

```lua
client.text_input_begin('начальный текст') -- скрытое поле забирает клавиатуру: любая раскладка, вставка
local text, active, cursor = client.text_input_get() -- active=false, когда поле отпустили (Enter, клик мимо)
client.text_input_end()
renderer.avatar(x, y, w, h, r, g, b, a, radius) -- аватар своего игрока, radius = скругление
```

## Игровые события

Callbacks ниже получают копии публичных данных и выполняются через обычную очередь событий (64 ожидающих / до16 callback-вызовов за кадр). Это API текущих механик игры, а не полный набор событий Source/Roblox. Подписка не даёт доступа к Instances или закрытым серверным углам.

| События | Данные / источник |
| --- | --- |
| `weapon_fire`, `bullet_impact` | Подтверждённый `shot`, плюс `slot=shooter`, `observed=false`. Fire включает нож; impact — только пули. Дополнительные жертвы одной пробившей пули не создают повторный fire/impact. |
| `player_hurt` | Подтверждённый выстрел: `slot=victim`, `attacker=shooter`, `damage`, `health`, `group`, `killed`, `start`, `impact`, `weaponId`, `cmdNumber`, `tick`, остальные поля shot. Урон от падения/бомбы отслеживается через `player_health`, без выдуманного attacker. |
| `player_death` | Подтверждённый смертельный shot с полями hurt либо наблюдаемый переход в dead: `{slot,tick,origin,weaponId,observed=true}`. Смерть, уже замеченная по snapshot, повторно из shot не выдаётся; сведения о выстреле остаются в `shot`/`player_hurt`. |
| `aim_hit`, `aim_miss` | Результат собственного rage-shot: поля shot, `target`, `slot=aimTarget`, строка `reason` при наличии диагноза сервера. Не предсказание и не результат trace_bullet. |
| `player_connect`, `player_disconnect` | `{slot,player}` из roster. Первый полученный roster показывает уже присутствующих игроков как connect. |
| `player_team` | `{slot,team,old_team}`. Смена пользователя в занятом слоте сбрасывает наблюдение его жизни. |
| `player_score` | `{slot,player,previous}` при изменении kills/deaths/assists/score. |
| `player_spawn` | `{slot,tick,origin,weaponId,observed=true}` при первом живом snapshot или переходе dead → alive. |
| `weapon_switch`, `weapon_reload`, `weapon_reload_end` | Наблюдаемые `{slot,tick,origin,weaponId,observed=true}`, switch добавляет `old_weaponId`. Reload_end означает исчезновение состояния reload, включая прерывание. |
| `weapon_ammo` | `{slot,tick,weaponId,clip,reserve,observed=true}`. |
| `player_jump`, `player_land`, `player_scope`, `player_duck` | Переходы публичных состояний. Общие slot/tick/observed; scope добавляет `zoom` (у других игроков только0/1), duck — boolean `duck`. Jump означает отрыв от земли, включая падение с края. |
| `player_health`, `player_armor` | `{slot,tick,health/armor,previous,observed=true}` при изменении соответствующего snapshot-поля; изменение HP может объединять несколько источников урона/лечение/respawn. |
| `round_start`, `round_end`, `round_freeze_end`, `match_start`, `match_end` | Публичное состояние матча: freeze, ended, live, начало первого раунда, complete соответственно. |
| `round_phase` | `{phase,previous,round,tick}` при смене фазы. |
| `round_mvp` | `{mvp,round,tick}` при завершении раунда с MVP. |
| `bomb_pickup`, `bomb_dropped`, `bomb_planted`, `bomb_defused`, `bomb_exploded` | `{bomb,tick,round}` при переходах публичного состояния бомбы. |
| `bomb_state` | `{bomb,previous,tick,round}` при смене state или carrier. |
| `bomb_beginplant`, `bomb_abortplant`, `bomb_begindefuse`, `bomb_abortdefuse` | `{slot,action,tick}`. Успешное действие не выдаёт abort; завершение определяется через planted/defused. |
| `bomb_equipped` | `{slot,equipped,tick}` при доставании/убирании C4. |

Snapshot-события описывают **замеченные переходы**: потерянные или пропущенные промежуточные состояния не восстанавливаются. Shot/roster/match используют существующие серверные сообщения; сеть не расширяется. У `player_death` следует учитывать `observed`, а для каждого попадания пользоваться `player_hurt`/`shot`. События не переигрываются при загрузке Lua посреди матча.

## Управление rage

Синхронные callbacks идут в порядке загрузки Lua, получают отдельную копию таблицы. Изменяй поля таблицы; возвращаемое значение не используется. Они работают только в обычном пути встроенного gun-rage (не knifebot), под общим бюджетом VM. Числовые поля проверяются на finite/range, неизвестные поля игнорируются. `skip=true` нельзя отменить из следующего скрипта. Ошибка/выгрузка убирает hooks; постоянные изменения store не нужны.

| Callback | Что можно менять |
| --- | --- |
| `rage_config(c)` | Настройки одного вызова rage: `enabled`, `autoFire`, `autoStop`, `autoScope`, `autowall`; `minDamage`0..130, `hitchance`0..100, `headScale`/`bodyScale`0..100, `safe`/`body`1..3 (Off/Prefer/Force), `fov`0..180, `backtrack`1..3 (Off/Last/All); `hitboxes`/`multipoint` — ровно6 boolean: head/chest/pelvis/arms/legs/feet. `lethal` (boolean): нужный урон = HP цели вместо minDamage (в меню это «FL» — слайдер минимального урона на 101; тогда `minDamage`=100, `lethal`=true). Read-only контекст `cmdNumber`, `weaponId`, `group`, `group_name`, `doubleTap`, `stopOpts`. PLAYERS overrides продолжают применяться. |
| `rage_target(t)` | `skip`, `priority`, `score`(-1e6..1e6). Контекст: `slot`, `health`, `origin`, `fov`. Цели сортируются priority → score → FOV. Нельзя вернуть whitelisted/dead/friendly цель. |
| `rage_record(r)` | `skip`, `score`; контекст `slot`, `tick`, `backtrack`, `origin`. Только уже допустимые по времени записи; нельзя навязать недопустимый tick. |
| `rage_point(p)` | `skip`, `score`; контекст `slot`, `tick`, `backtrack`, `point`, `hitbox`, `group`, `damage`, `safe`, `center`, `fov`. Вызывается для точек, уже прошедших world/damage/safety; score прибавляется к встроенному рангу и score записи. Позволяет выбирать среди валидных точек, не подменяет их координаты. Может вызываться много раз — держи callback коротким. |
| `rage_fire(s)` | `skip` — окончательный запрет выстрела после ideal/HC проверок, с возвратом обычного движения. Контекст `slot`, `point`, `hitbox`, `damage`, `hitchance` (нижняя оценка), `required_hitchance`, `minDamage`, `backtrack`, `cmdNumber`. |

Обычные world/damage/HC/safe проверки и серверная валидация выполняются после выбора. Hooks сами по себе не дают идеального знания spread/углов или гарантии попадания. В отсутствие активных hooks встроенный выбор не меняется. Пример: `lua-examples/rage-hooks.lua` (опции выключены по умолчанию).

## Камера

`camera.get()` возвращает фактические `{position,pitch,yaw,roll,fov}`; position в hu, углы в градусах, FOV горизонтальный в принятой игрой системе. `client.camera_position()` возвращает x,y,z в hu; `client.camera_angles()` по-прежнему возвращает **входные** pitch,yaw игрока.

```lua
client.set_event_callback('override_view', function(v)
    v.thirdperson=true; v.distance=100; v.fov=100
    v.position=v.position+vector.new(8,0,0)
    v.roll=5; v.collision=true
    v.viewmodel_fov=100; v.viewmodel_offset=vector.new(2,0,0)
    v.hide_viewmodel=false
end)
```

Callback вызывается каждый игровой render-frame для живого игрока вне main/team menu. Меняется только визуальная камера, не usercmd, прицел или серверные углы. Position — точка камеры/опора thirdperson в hu (сначала проверяется смещение от штатного глаза, затем отступ thirdperson). Distance0..240hu, pitch -89..89, roll -180..180, FOV20..150, viewmodel_fov40..140, viewmodel_offset по каждой оси ±48hu в локальных осях viewmodel. `collision=true` по умолчанию проверяет геометрию смещения и отступа. Death/spectator/menu camera остаются под управлением игры. Настройки вычисляются заново каждый кадр; unload/error сразу возвращает штатную камеру. Пример `lua-examples/custom-camera.lua` (выключен по умолчанию).

## 3D-маркеры и эффекты

```lua
local id=renderer.effect('ring', position, {
    radius=8, width=.5, normal=vector.new(0,1,0),
    color={125,209,255,255}, life=1, fade=.3,
})
renderer.update_effect(id,{position=newPosition,color={255,100,100,255}})
renderer.remove_effect(id)
renderer.clear_effects()
```

Типы `sphere`, `box`, `ring`, `text`, `light`, `particles`. Это локальные engine-объекты с обычным depth testing; не экранные рисунки. Вызывай при событии, а не заново каждый paint; для перемещения используй update_effect. Только свои числовые handles. Координаты, размеры, radius/width/range и скорости — hu; время — секунды.

- Общие: RGBA `color`, `life`.05..10, `fade`0..life; `rotation` Vector3 углов в градусах для box/sphere. `material` neon/smooth/glass.
- Sphere: `radius`.1..240; box: положительный Vector3 `size` до480 по оси.
- Ring: `radius`, `width`.05..24, ненулевой `normal` (компоненты ±1);24 прямых Beam-сегмента в плоскости нормали.
- Text: `text` до128 байт, `text_size`8..48; BillboardGui с `AlwaysOnTop=false`.
- Light: `brightness`0..4, `range`1..240; PointLight без теней; alpha/fade меняют яркость.
- Particles: разовая вспышка, `count`1..64, `speed`0..600, `spread`0..180, `acceleration` Vector3 до±1200 на ось; `radius` — размер частицы; необязательный `texture='rbxassetid://...'`, по умолчанию встроенная sparkle. Частицы используют собственное затухание на протяжении life; общий fade для этого типа не применяется.

Максимум32 активных эффекта /16 новых за render-frame /4 активных света на скрипт. Невидимые anchors не участвуют в collision/touch/query. `update_effect` меняет position/color/text и возвращает false для истёкшего handle; срок жизни не продлевается. Expiry, unload/reload/error удаляют всё. Визуальное свечение зависит от Lighting; API не включает Bloom принудительно. Пример `lua-examples/impact-effects.lua` использует реальные bullet_impact/player_hurt.

## Игровой контекст

- `entity.get_local_player()` — номер слота.
- `entity.get_players(enemiesOnly)` — слоты из последних публичных снимков; проверяй здоровье/flags самостоятельно.
- `entity.get(slot)` — копия публичного снимка: `origin` (Vector3, hu), `yaw`, `foot`, `pitch`, `duck`, `flags`, `health`, `armor`, `weaponId`, `clip`, `reserve`, `choked`, `packetId`, `team`, `tick`, публичные анимационные слои.
- `entity.get_local_state()` — копия локального состояния: `move`, `weapon`, `anim` и другие поля симуляции. Запись в копию игру не меняет.
- `entity.get_name(slot)`, `is_alive(slot)`, `is_enemy(slot)`, `get_origin(slot)` (x,y,z), `get_weapon(slot)` (copy of weapon definition), `get_local_weapon()` (local held weapon definition).
- `entity.get_prop(slot,'move.weight')` reads a public snapshot path; `entity.get_history(slot,count)` returns up to32 snapshots in chronological order, copied.
- `entity.get_hitboxes(slot,footYaw?,tick?)` returns public-pose boxes `{name,group,origin,size,radius,transform}`; transform is a CFrame value. Optional footYaw is YOUR hypothesis, not a revealed real angle. Optional tick samples public history. Up to 64 pose builds per script per frame (their time counts against the 10 ms frame budget).
- `antiaim.get_condition()` — `standing`, `moving`, `in air` либо `shared` до получения состояния.
- `globals.realtime()`, `globals.curtime()` (серверное время), `globals.tickcount()`, `globals.frametime()`.
- `client.screen_size()`, `client.key_state('K')`, `client.log(...)`, `print(...)`.
- `client.mouse_position()`; `key_state('Mouse1'/'Mouse2')`; `client.camera_angles()` (input pitch,yaw), `client.latency()` (server latency estimate in seconds), `client.get_match()` (public match copy).
- `globals.tickinterval()` (1/64), `globals.server_tick()` (last snapshot), `globals.framecount()`.
- `vector.new(x,y,z)` — Roblox Vector3; `buttons` — константы кнопок игры; `bit` — основные функции bit32.

## Трассировки и управление целями

`client.trace_line(fromVector,toVector)` accepts hu and returns `{hit,fraction,position,normal}`. Map/bullet geometry only; no player Instances. Up to 128 queries per frame per script, segment up to 8192 hu.

`client.trace_bullet(slot,fromVector,toVector,footYaw?,tick?)` traces an ideal bullet along that direction (up to the held weapon's range), using the local held weapon, public target pose and normal penetration/damage rules. Optional tick samples public target history. Returns `{damage,hitbox,group,distance,penetrated,position}` or damage0. Also consumes one pose build; it does not sample weapon spread/HC or guarantee a real server hit. Real server angles remain unavailable.

```lua
rage.get_status()
rage.get_target_override(slot) -- copy of PLAYERS adjustment
rage.set_target_override(slot, {priority=true, forceBody=true, bodyYaw=-30})
rage.reset_target_override(slot) -- release this script's overrides for the target
```

Allowed target fields: `whitelist`, `priority`, `forcePitch`, `forceBody`, `correction` (booleans), `pitch`(-89..89), `bodyYaw`(-58..58), `bodyAim`/`safePoint`(1..4, same indices as PLAYERS). Overrides are local, stacked between scripts and restored on unload/error. Target must exist in the public roster. Up to160 override fields per script.

## Таймеры, состояние и утилиты

```lua
local id = client.delay_call(1, function(value) client.log(value) end, 'hello')
local repeating = client.every(.25, function() client.log('tick') end)
client.cancel_timer(id)
storage.set('panel_x', 100)
local x = storage.get('panel_x')
storage.clear()
```

Up to32 timers, repeating interval >=0.05s; no catch-up burst after a slow frame. Callbacks run as threads (see "Потоки" below) and share the VM/frame budget. `storage` is private per script NAME, survives unload/reload in this game session, but is **not cloud persistence**. Up to64 keys /16KiB JSON per script; keys <=40 bytes. Rejoining clears it.

`utils.lerp`, `clamp`, `normalize_yaw`, `angle_diff`, `smoothstep`, `json_encode`, `json_decode` (JSON up to16KiB).

Строки и таблицы (нативные функции работают вне бюджета VM, поэтому ограничены размером): `string.rep`, `reverse`, `format`, `split`, `table.concat` — до 4 MiB результата; `table.create`/`move` — до 1 048 576 элементов; `table.sort` — до 65 536. `find`, `match`, `gmatch`, `gsub`: шаблон до 256 байт, текст до 16 KiB; текст до 4 MiB — для `find(..., true)` и для шаблонов без перебора (без `*`, `-`, `%b` и с одним `+` только в конце: `.`, `%x%x`, `[^,]+`, `%d+`). `gsub` с функцией или таблицей выполняется в Luau, а не нативно: колбэк считается в бюджете, а большой декодер в потоке растягивается на несколько кадров. Строковые методы (`s:rep()`, `s:gsub()`...) идут через те же функции, `getmetatable('').__index` — эта же библиотека.

Ещё доступно: `os.clock/time/date/difftime`, `setmetatable/getmetatable` (не на таблицах, которые отдала игра), `newproxy`, `rawget/rawset/rawequal/rawlen`, `_G`, `getfenv()` (окружение скрипта), `coroutine` (create/resume/yield/wrap/status/running/isyieldable/close — только свои), `utf8`, `bit32`, `bit` (+ `tobit/tohex/arshift/rol/ror/...`), `buffer` (до 4 MiB), `string.pack/unpack/packsize`, `math.modf/log10/frexp/ldexp/noise/cosh/sinh/tanh/map/lerp`, `collectgarbage("count")`, `debug.traceback` (заглушка, без доступа к стеку). `pcall` / `xpcall` возвращают ошибки как обычный Lua: `error(msg, 0)` приходит ровно `msg`, позиционные ошибки выглядят как `имя:строка: сообщение`, таблица-ошибка остаётся таблицей. Исчерпание бюджета поймать нельзя. Copies are limited to depth5,256 entries/table and4096 visited values per operation.

## Потоки: task, wait, авто-yield

Код, результат которого не нужен прямо в этом кадре, работает в потоке: загрузка скрипта (main chunk), очереди событий (`shot`, `player_hurt`, `round_start`...), таймеры, кнопки, колбэки `gui.*`, `task.*`. Когда поток выбирает 10 ms кадра, он **не падает**, а продолжается со следующего кадра — тяжёлую загрузку, декодирование или цикл ожидания можно писать прямо:

```lua
task.spawn(function()
    while true do
        client.log('tick')
        task.wait(1)         -- поток спит 1 s, кадр не занят
    end
end)
local co = task.delay(5, function(msg) client.log(msg) end, 'через 5 s')
task.cancel(co)
task.defer(function() end)   -- со следующего кадра
local dt, now = wait(0.5)    -- алиасы: wait / spawn (= task.defer) / delay
```

До 64 потоков на скрипт (вместе с ждущими), выгрузка закрывает все. Загрузка скрипта получает сразу до 2 s, дальше идёт по 10 ms за кадр, всего не больше 30 s времени VM. Колбэки, которые игре нужны в этом кадре — `paint`, `paint_ui`, `setup_command`, `anti_aim`, `resolve`, rage-хуки, `override_view`, `shutdown` — по-прежнему прерываются на бюджете, и `task.wait`, `readfile` до загрузки workspace и синхронный HTTP там дают понятную ошибку (запусти работу через `task.spawn`). Внутри нативного вызова (компаратор `table.sort`, метаметоды) уступить кадр нельзя, такой вызов тоже прерывается.

## load / loadstring

```lua
local f, err = loadstring('return 1 + ...', 'chunk')
print(f(2))                  -- 3
local g = load(function() return nextPiece() end)  -- форма с reader
```

Компилирует тот же компилятор в ту же песочницу и с тем же бюджетом. Ошибка компиляции возвращается как `nil, сообщение`. Только исходник: байткод (`\27...`) не принимается. До 400 KiB на кусок, 256 кусков на скрипт; компиляция не тратит бюджет VM, но длинная заморозит кадр.

## HTTP

```lua
-- в потоке (загрузка, события, task.spawn): выглядит синхронно
local body = game:HttpGet('https://example.com/data.json')
local r = request({Url = 'https://api.site/x', Method = 'POST', Headers = {['Content-Type'] = 'application/json'}, Body = '{}'})
print(r.StatusCode, r.Body)            -- также r.status, r.body, r.headers, r.success
local r2 = http.get('https://example.com/')
-- в paint и других колбэках этого кадра — только с колбэком:
http.get('https://example.com/', function(success, response) print(response.status) end)
http.post(url, body_or_options, callback)
http.request('PUT', url, {headers = {...}, body = '...'}, callback)
```

Также `http_request` и `syn.request`. Запросы идут через сервер игры: любые `http://` / `https://` адреса, кроме доменов Roblox и локальных адресов. Перед первым запросом скрипта к новому домену игрок видит окно «Разрешить / Запретить»; разрешённые домены запоминаются, запрет действует до перезахода. Лимиты: 5 запросов сразу и дальше 30 в минуту на игрока, 3 одновременно, 8 ожидающих на скрипт, 120 в минуту на сервер; тело запроса до 256 KiB, ответ до 1 MiB, таймаут 40 s. Каждый новый домен игрока попадает в журнал безопасности. Discord-вебхуки не обещаем (Discord режет запросы с серверов Roblox).

## Файлы (workspace)

```lua
makefolder('mycfg')
writefile('mycfg/main.json', utils.json_encode(settings))
appendfile('log.txt', 'line\n')
if isfile('mycfg/main.json') then settings = utils.json_decode(readfile('mycfg/main.json')) end
for _, path in listfiles('mycfg') do print(path) end   -- прямые потомки; '' = корень
delfile('log.txt'); delfolder('mycfg'); isfolder('mycfg')
```

Один workspace на игрока, общий для всех его скриптов (как у экзекуторов: конфиги, кэш лоадеров), хранится на сервере и переживает перезаход. Пути: буквы, цифры, пробел, `. _ - /`, до 120 символов и 8 папок, без `..`. Только текст (UTF-8; бинарные данные кодируй, например в base64). Лимиты: файл до 256 KiB, всего 1 MiB и 200 файлов. Чтение — из кэша клиента, запись сразу видна скриптам и сохраняется сервером (не чаще раза в 30 s и при выходе). Workspace подгружается при входе; если обратиться раньше, поток подождёт, а `paint` получит ошибку.

## Закрытые скрипты

В меню Lua: **Publish sealed** компилирует исходник из редактора на твоём клиенте без отладочной информации (без имён локальных переменных и номеров строк) и отправляет на сервер только байткод; сервер проверяет его и выдаёт код из 8 символов. **Load by code** — любой, у кого есть код, запускает скрипт; исходник при этом нигде не появляется (ни в меню, ни в `print`, ни в `load`). **My sealed scripts**, **Delete sealed (code)** — список и удаление своих. Повторная публикация под тем же именем сохраняет код. Лимиты: исходник до 1 MiB (большой скрипт заморозит игру автора на несколько секунд один раз при публикации), 10 скриптов и 2 MiB байткода на автора, публикация раз в 20 s. Скрипты больше 400 KiB запускаются только так — загрузка по коду не компилирует.

### Облако: Cloud → Show: Lua

Сохранённый скрипт публикуется из вкладки Cloud (Show: Lua → Publish). **Приватный** — только по коду, в списке его нет. **Публичный** — в общем списке с рейтингом, загрузками, поиском и сортировкой, как облачные конфиги. **Open source** хранит исходник (до 400 KiB): любой может нажать «Save to my scripts» и получить код в Config → Lua. **Closed source** — только байткод, из списка его можно лишь запустить. Повторная публикация под тем же именем обновляет скрипт, а смена флагов убирает его из списка или возвращает. Один лайк или дизлайк на игрока, загрузка считается один раз. Имена публичных скриптов проходят фильтр Roblox, исходники open source проверяются на запрещённые слова. Админы могут удалить любой публичный скрипт.

## Защита кода от копирования

Полностью защитить Lua-скрипт от кражи нельзя: любой код, который выполняется на клиенте, можно выдрать экзекутором из памяти. Можно сильно усложнить:

- **Закрытые скрипты** (выше) — исходник не покидает автора, у остальных есть только байткод без имён и строк. Байткод можно декомпилировать, но результат без имён читать тяжело.
- **Обфускатор поверх** — Prometheus (пресеты Minify, Weak, Vmify, Medium проверены, у Strong есть проблемы), luaobfuscator, MoonSec, Luraph и подобные. Песочница даёт им то, что они обычно используют: `getfenv`, `newproxy`, `getmetatable('')`, `bit32`, `buffer`, `string.pack`, большие строки, ошибки `pcall` как в обычном Lua.
- Лучше всего — обфускатор, а результат опубликовать закрытым.

## Свой резольвер, AA, правила выстрела, кейбинды

Всё ниже — копии публичных или своих локальных данных; реальные углы других игроков не раскрываются.

**Резольвер.** `entity.get_history(slot)` уже содержит поля, которые встроенный резольвер считает по каждому снимку: `resolverMax` (ширина десинка из публичного движения), `resolverJump` (знак последнего прыжка yaw), `resolverJitter`, `resolverPacket` (номер пакета игрока, его чётность едет в каждой команде), `resolverCond` (1 общее, 2 стоит, 3 в воздухе, 4 бежит, 5 слоу-вок), `resolverMovingAt`/`resolverMovingYaw` (LBY в движении), `resolverLbyAt`, `resolverFake` (чокал в последние 3 с), `resolverPrevYaw` (yaw прошлого пакета), плюс `lby`, `choked`, `packetId`, `move` (`strafeDir`, `strafeWeight`, `cycle`, `weight`).

```lua
resolver.get_mode()                        -- 'off' / 'default' / 'bruteforce' / 'opposite' (меню)
local foot,max=resolver.get_builtin(slot,tick?,mode?) -- корпус встроенного резольвера, без Lua resolve
resolver.trusts_public(slot,tick?)         -- игрок без чока: публичный корпус = реальный
resolver.is_confident(slot)                -- встроенный Default уверен
resolver.get_bullets(slot,tick?)           -- вражеские пули в 32 hu от глаз к тику (антибрут), nil до первой
resolver.fired_at(slot,tick)               -- на этом тике игрок сам стрелял (AA выключен, корпус от прошлого пакета)
```

`resolve` может вернуть `{foot=угол, confident=true}`: уверенность заменяет встроенную для «Prefer safe point if unresolved». Событие `shot` приходит по всем выстрелам сервера (`start`, `impact`, `group`, `victim`, `tick`) — по попаданиям любого игрока можно перебирать гипотезы:

```lua
-- луч только по хитбоксам (без карты и урона): какой хитбокс пересекает путь пули при гипотезе
local hit=entity.trace_hitboxes(slot,e.start,e.impact+(e.impact-e.start).Unit*64,foot,tick) -- {hitbox,group,position,distance} или nil
-- хитбоксы свободной позы (своя голова при другом yaw / корпусе)
local boxes=entity.build_hitboxes({origin=vector.new(x,y,z),yaw=0,foot=58,pitch=89,duck=0,weapon_id=40})
local ex,ey,ez=entity.get_eye_position(slot?) -- глаза (без slot — свои)
-- гранаты в полёте и активные смоки (только режим с гранатами), hu и секунды
for _,g in entity.get_grenades() do
    -- g.id, g.type ('he'/'smoke'/'molotov'/...), g.thrower (слот), g.origin, g.velocity (Vector3), g.bounces,
    -- g.active (смок уже дымит). Пока летит: g.time_left (до детонации), g.path (предсказанный остаток пути,
    -- каждый 4-й тик + конец), g.bounce_points, g.landing (где сработает)
end
```

Предсказание — та же GrenadeSim, что на сервере, по карте без игроков; после каждого отскока сервер присылает точное состояние и путь пересчитывается. Во встроенном меню то же самое: Visuals > Effects «Thrown grenade trajectory» (Own / Teammates / Enemies) и «Trajectory through walls».

`entity.trace_hitboxes` и `build_hitboxes` принимают слот или таблицу позы и считаются в лимит поз (64 за кадр).

**AnimState** — та же симуляция анимации, что у сервера (реальный корпус) и у публичного тела (шаг на пакет). Хэндлы приватные, до 32 на скрипт:

```lua
local a=animstate.new()
local st=animstate.step(a,{eye_yaw=yaw,velocity=vel,on_ground=true,duck=0,max_speed=230,scoped=false,dt=1/64,now=t,lby=nil,walk=false})
-- st: копия состояния (foot, lby, maxDesync, walkToRun, velX, velZ, ...)
local b=animstate.clone(a);animstate.free(b);animstate.get(a)
animstate.start_cycle(moveYaw)             -- ANIMTAG_STARTCYCLE слоя бега для move yaw (nil — нет тега)
antiaim.get_public_state()                 -- своё публичное тело (что видят другие)
```

**Правила выстрела.** `rage.get_last()` → `{status,target,cmd_number,firing}` последнего вызова рейджа (каждая команда, а не метка меню 5 Гц); `rage.get_status()` теперь тоже последний. `rage.predict_damage(group,distance,armor?,weaponId?)` — урон CS по группе (`head/neck/chest/stomach/arm/leg/generic`) на дистанции hu с учётом брони, текущим оружием или по id. `exploits.get_status()` → `{double_tap='ready'|'charging'|nil,charge,max_charge,fake_duck,hide_shots}`.

**Кейбинды.** `ui.get_binds()` → `{key,name,check,enabled,bind_key,mode,active}` по всем биндам меню (встроенным и скриптовым) — для своего списка кейбиндов. `ui.set_bind_held(key,down)` нажимает/отпускает собственную клавишу бинда, как тач-кнопки: Hold активен, пока держишь, Toggle переключается на нажатии (нажать + отпустить), OffHotkey наоборот. Можно для AA/Rage/Visuals/World/Misc и своих хоткеев; удержания снимаются при выгрузке. Клавишу и режим бинда меняет `ui.set_setting(key,{Key='None',Mode='Toggle'})`.

**Меню и HUD.** `ui.get_setting_info(key)` → `{type,min,max,integer,options,default}` (`checkbox/slider/combo/multiselect/color/hotkey/text`, у комбобоксов названия опций) — чтобы собрать свою страницу с теми же пунктами. `ui.set_builtin_indicators(false)` прячет левые индикаторы DT/DUCK/ONSHOT, пока скрипт загружен; список кейбиндов и вотермарк выключаются настройками Misc. `client.set_smoke_hidden(true)` — локально убирает дым гранат (как Visuals > Effects «Remove smoke grenades»; дым скрыт, если просит меню или любой скрипт). `globals.render_tick()` — дробный тик интерполяции, на котором рисуются игроки (`entity.get_hitboxes(slot,foot,globals.render_tick())` = хитбоксы ровно там, где модель).

**Звук.** Событие `player_sound` `{slot,kind,position,tick}`: шаг (`step`), прыжок (`jump`), приземление (`land`), ступенька лестницы (`ladder`) другого игрока, которые клиент проигрывает — для sound ESP.

## Своё меню: gui.*

Встроенная библиотека виджетов на нативных объектах Roblox: рисуется движком, а не через 384 примитива `paint`, поэтому почти не тратит бюджет скрипта. Набор текста, скролл, перетаскивание и попапы работают сами. Пока окно открыто, курсор свободен, а стрельба, движение и камера стоят, как при открытом чит-меню. Полный пример: `lua-examples/gui-showcase.lua`.

```lua
local win=gui.window({title='my script',subtitle='v1.0',width=680,height=480,
    theme='default',        -- 'default' / 'gamesense' / 'neverlose' или таблица (ниже)
    key='RightShift',       -- клавиша открыть/закрыть (по умолчанию RightShift; false — без клавиши)
    follow_menu=false})     -- true: окно видно только вместе с чит-меню (без клавиши и крестика)
local tab=win:tab('Rage')                  -- вкладки сбоку или сверху (theme.tabs)
local g=tab:group('Aimbot','left')         -- две колонки: 'left' / 'right' (по умолчанию по очереди)

local on=g:toggle('Enabled',{default=true,flag='on',bind='K',mode='Toggle'}) -- bind: свой кейбинд справа
local fov=g:slider('FOV',0,180,90,{step=1,suffix='°',flag='fov'})
local box=g:dropdown('Hitbox',{'Head','Chest'},1,{flag='hb'})
local pts=g:multiselect('Points',{'Head','Chest','Legs'},{true},{flag='pts'})
local col=g:color('Color',255,90,120,255,{flag='col'})
local txt=g:textbox('Tag','hi',{placeholder='text',flag='tag'})
local key=g:keybind('Peek','X','Hold',{flag='peek'})      -- ЛКМ — назначить, ПКМ — режим
g:label('Любой текст');g:button('Run',function() gui.notify('done',{title='my script'}) end)
```

Элементы: `get()`, `set(v)`, `on_change(fn)` (колбэк через очередь событий скрипта, со значением), `set_visible(b)`, `set_enabled(b)`, `set_label(s)`. Значения: toggle — boolean, slider — число (шаг `step`, `format` вида `'%.1f'`), dropdown — индекс с 1 (`set` принимает и название, `get_option()` — название, `set_options(list)`), multiselect — массив boolean (`get_option()` — выбранные названия), color — `{Color=Color3,Alpha=0..1}` (`set` принимает Color3, `{r,g,b,a}` или `{Color,Alpha}`), textbox — строка до 256 байт, keybind — активен ли (`get_key()` → key, mode; `set('K','Toggle')`). У toggle с `bind` есть `is_active()` = включён и бинд активен. Свои бинды попадают в список кейбиндов меню и работают как встроенные (Hold / Toggle / Always / OffHotkey).

**Привязка к настройкам игры:** `{link='Rage.doubleTap'}` (toggle), `link` у slider (диапазон из настройки), dropdown/multiselect (названия опций из настройки), color, keybind (`{link='Rage.doubleTapKey'}`), у toggle ещё `bind_link='...Key'`. Такой элемент меняет настройку так же, как встроенное меню (сохраняется в конфиг, не откатывается при выгрузке), и обновляется, если её поменяли в меню. Можно для AA / Rage / Visuals / World / Misc; настройка должна существовать (`pcall(ui.get_setting_info,key)`).

**Окно:** `set_open(b)`, `is_open()`, `set_theme(t)`, `set_title(s)`, `get_position()`, `set_position(x,y)`, `set_size(w,h)`, `export()` → `{flag=value}` значений с `flag` (привязанные к игре не входят — они в конфиге игры), `import(t)`. Сохранить между перезагрузками скрипта: `storage.set('menu',win:export())`.

**Темы:** пресет или таблица `{preset='neverlose', accent={0,148,255}, background=..., panel=..., element=..., hover=..., border=..., text=..., subtext=..., rounding=0..16, font='gotham', title_font='gotham_bold', text_size=9..20, transparency=0..0.9, toggle='switch'|'checkbox', tabs='side'|'top'}` (цвета — Color3 или `{r,g,b}`). `gui.themes()`, `gui.fonts()` — списки (`gotham`, `gotham_bold`, `code`, `ui`, `ui_bold`, `roboto`, `roboto_mono`, `ubuntu`, `montserrat`, `nunito`, `arial`, `arial_bold`).

**Уведомления:** `gui.notify(text,{title=...,duration=4,color={r,g,b}})` — тосты справа снизу, до 6.

**Свой интерфейс на renderer:** событие `input` `{kind='key'|'mouse'|'wheel',key,down,x,y,delta,typing,game}` (клавиши, кнопки мыши, колёсико); `client.capture_input(true)` освобождает курсор и держит ввод игры, пока не вернёшь `false`; `client.is_input_captured()`.

Лимиты: 4 окна, 16 вкладок на окно, 600 элементов на скрипт. Выгрузка скрипта убирает окна, бинды и захват ввода.

## Совместимость с gamesense

Формы gamesense распознаются по аргументам, родной API работает как раньше:

- `ui.new_checkbox/slider/combobox/multiselect/color_picker/hotkey/button/label/textbox("TAB", "Group", "Name", ...)` — путь меню отбрасывается, имя становится подписью. Комбобокс/мультиселект принимают опции списком аргументов; у таких контролов `ui.get` возвращает название опции (мультиселект — список названий), `ui.set` принимает названия. `ui.contains(id, "Option")`. `new_hotkey(..., true)` (inline) работает.
- `renderer.text(x, y, r, g, b, a, flags, max_width, ...)` — текст склеивается из аргументов; флаги `c` центр, `r` справа, `b` жирный, `-` мелкий, `+` крупный. `renderer.measure_text(flags, ...)`. `renderer.circle(x, y, r, g, b, a, radius, start_degrees, percentage)`, `renderer.circle_outline(..., thickness)`, `renderer.indicator(r, g, b, a, ...)` (стек слева, возвращает y).
- `client.key_state(vk)` с виртуальными кодами Windows (`0x01` ЛКМ, `0x41` A, `0x70` F1...), `client.color_log`, `random_int`, `random_float`, `unix_time`, `system_time`, `userid_to_entindex` (здесь id = слот).
- `globals.absoluteframetime`, `mapname` (`de_mirage`), `maxplayers`.
- `entity.get_prop(slot, "m_iHealth" | "m_ArmorValue" | "m_fFlags")`, `"m_vecOrigin"` возвращает x, y, z.
- `require "vector"`: `vector(x, y, z)` с полями `x/y/z`, операторами и методами `length`, `length2d`, `dist`, `dot`, `cross`, `normalized`, `normalize`, `angles`, `lerp`, `unpack`, `toVector3`. `vector.new(x, y, z)` по-прежнему даёт Vector3. `require "bit"` = `bit`.
- `client.set_event_callback` с неизвестным событием (`run_command`, `net_update_start`, ...) не роняет скрипт: callback игнорируется, после загрузки выводится список проигнорированных событий.

Недоступно: FFI, `require "gamesense/..."`, `ui.reference` по названиям меню gamesense (используй ключи `ui.list_settings()`), netprops кроме перечисленных.

## Выполнение и ограничения

Текст компилируется локальным LuauCeption (Luau 0.700), байткод исполняется Fiu. Исходники хранятся сервером как данные и никогда не исполняются на сервере. Нет доступа к настоящим `game` (есть только `game:HttpGet/HttpGetAsync/HttpPost`), `workspace`, `require`, окружению вызывающего кода, debug, Instances, remotes и FFI. Стандартная библиотека предоставлена в ограниченном виде (см. выше); protected calls и корутины сохраняют лимиты исполнения. Ошибки показываются как `line N (функция): сообщение [from line M <- ...]`.

До 20 сохранённых/загруженных скриптов, **запуск и сохранение до 400 KiB исходника** (больший — только как закрытый скрипт, до 1 MiB; поле Roblox TextBox ограничено 200 000 байт, больший исходник вставляется частями), **1 MiB всего сохранённых Lua на игрока**, 48 контролов, 16 обработчиков одного события, 384 рисунка за кадр на скрипт. Бюджет VM — 10 ms на скрипт за кадр: колбэки этого кадра прерываются, потоки продолжаются со следующего кадра (загрузка — до 2 s сразу, до 30 s всего). Ошибка или превышение бюджета в callback прерывает только этот вызов, скрипт продолжает работать; выключает скрипт только ошибка при загрузке. Это не жёсткая изоляция памяти: компилятор и нативные библиотечные операции работают в том же Roblox-клиенте; бюджет VM не является гарантией максимальной паузы любой операции. Мобильная производительность и ощущение в live multiplayer требуют проверки владельцем.

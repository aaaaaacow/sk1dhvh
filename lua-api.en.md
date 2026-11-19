# Lua in HvH

**Русская версия:** [lua-api.md](lua-api.md)

Config tab: configs and their export on the left, Lua on the right. Paste the source, give it a name and press **Load / reload** (a source larger than ~195 KiB is pasted in parts with **Add as part**). **Save source** stores the source in your private profile; picking a saved script opens it in the editor. Scripts never start by themselves. **Unload** removes the script's callbacks, drawings and controls and reverts its AA/Rage changes. **Delete saved** deletes the saved source and unloads that script. Saving a source does not save the values of its controls.

Start with the [quick start](lua-guide.en.md). Ready starter scripts: `lua-examples/starter-hud.lua` (one element at a time: FPS / graph / shapes) and `starter-hitlog.lua` (your real shot results and optional 3D tracers). Other examples: `visuals.lua`, `aa-builder.lua`, `resolver.lua`, `images.lua`. Extended: `extended-visuals.lua` (draggable panel, clipping and graphics, on right away), `aa-builder-extended.lua` (five conditions; enabled with a checkbox). gamesense Lua scripts are not drop-in compatible: this is our own API, without FFI or game DLLs.

## Events

`client.set_event_callback(name, function)` / `client.unset_event_callback(name, function)`.

| Name | Argument and behavior |
| --- | --- |
| `paint` | Once per frame. This frame's drawings replace the previous ones. |
| `paint_ui` | After `paint`, same canvas and shared budget, also in the menu / lobby. |
| `net_update_end` | `{tick}` after a public snapshot was processed. Between frames only the latest snapshot is kept, no queue of stale packets. |
| `match_update` | Copy of the latest public match state; several updates in one frame are merged. |
| `round_start`, `round_end` | Public state when the round enters freeze / ended. |
| `aim_fire` | Predicted rage shot: `{cmdNumber,target,damage,hitchance,pitch,yaw,backtrack,tick,foot,fake,health,custom}` (`tick` = the target record, `foot` = the feet the shot assumed, `fake` = the target chokes, `custom` = a Lua `resolve` hypothesis). The server's result arrives separately as `shot`. |
| `setup_command` | Writable copy of the command before rage / AA. You can write `forwardmove`, `sidemove` (-127…127) and `buttons` (mask from the `buttons` table). The command number and network time are protected. Not called while the menu is open. |
| `anti_aim` | The command after the built-in AA. Write `yaw`, `pitch` (-89…89), `choke`, `send_packet`, `desync_amount` (0…58), `desync_side` (-1/1). A packet holds at most 16 commands (15 choked + the sent one, like sv_maxusrcmdprocessticks 16): `choke` / `send_packet=false` stop holding past that; the server runs longer packets only for a double tap shift / fake duck. `view_yaw`, `view_pitch`, `packet`, `chokedcommands` give context; read-only: `public_foot`, `public_lby`, `public_max_desync` (the public body others see: one AnimState step per sent packet), `real_foot`, `lby`, `max_desync` (the real one), `eye` (Vector3 hu), `fakelag_send` (fake lag's choice: true send, false choke, nil = fake lag not deciding). `bomb_action` (`'plant'` / `'defuse'` during a real plant / defuse, else nil), `legit_aa` (Legit anti-aim held: the built-in pitch / yaw stayed on the view). Movement is corrected automatically. Not called on ladders, while blocked or on an aimed rage shot. During a plant / defuse it runs only with AA > Other "Anti-aim on bomb actions" on (the player stays frozen, angles and desync keep running; fake lag pauses by itself for that time). A plain shot also restores the original angles. DT / FD and the packet length limit take priority over manual send / choke. |
| `resolve` | `{slot,yaw,foot_yaw,max_desync,tick,sample}`. Return an absolute assumed body (foot) yaw, a table `{foot=yaw, confident=true/false}`, or `nil` for the built-in algorithm. `confident` tells the built-in resolver whether the target counts as resolved (Prefer safe point if unresolved). Used when rage builds a pose, including interpolated records. Repeated requests for the same pose within one command are cached. |
| `shot` | Copy of the public `Net.UnpackShot` event: including `shooter`, `cmdNumber`, `damage`, `start`, `impact`, `flags`. |
| `shutdown` | The script is unloaded. Not called after a fatal error. |

Callbacks run in script load order. For conflicting commands / hypotheses the last valid result wins. The built-in resolver models do not learn from shots fired with a custom `resolve` hypothesis; the API never reveals real server angles. The resolver example demonstrates hypotheses; its accuracy is not verified.

## Menu and settings

Every constructor returns a numeric handle owned by the current script:

```lua
local on = ui.new_checkbox('Enabled')
local yaw = ui.new_slider('Yaw', -180, 180, 180)
local mode = ui.new_combobox('Mode', {'One', 'Two'})
local tint = ui.new_color_picker('Color', 160, 200, 80, 255)
local enabled = ui.get(on)
ui.set(on, true)
local r,g,b,a = ui.get(tint)
```

Combo boxes use 1-based indices. Controls appear below the Lua buttons; scroll to reach them.

More controls:

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

Callbacks, buttons and timers execute on the next render dispatch, outside native input handlers; at most 16 callbacks per frame per script, queue 64. Excess notifications may be dropped. Hidden hotkeys stay active. Unload removes hotkeys, callbacks, controls and timers. `ui.is_menu_open()` returns a boolean; `ui.menu_position()` returns screen x,y.

`ui.get_setting('AA.yawOffset')` returns a copy. `ui.list_settings('AA.')` lists the created controls. `ui.reference(key)` returns a script handle for an existing setting: `ui.get`, `ui.set`, `ui.set_callback` work on it, but hiding the original controls is not supported. Writes are allowed for AA / Rage / Visuals / World / Misc, not Admin / Config / Players. Numbers are validated against the actual slider / combo range; arrays must match the control's boolean options, colors accept `{r,g,b,a}` or a copied `{Color,Alpha}`, hotkeys accept `{Key='K',Mode='Hold'}`. Open the relevant menu section before referencing a conditional control that has not been created yet.

### Your own tab instead of a built-in one

```lua
ui.override_tab('AA')                 -- AA / Rage / Visuals / World / Misc / Players / Skins
local on = ui.new_checkbox('Enabled')
ui.set_group(on, 'Builder')           -- groupbox title (1..40 chars); default = script name
local yaw = ui.new_slider('Yaw', -180, 180, 0)
ui.set_group(yaw, 'Angles')
```

While the script is loaded, the tab's built-in groups are hidden and the script's controls take their place in their own groups (two columns, group order = order of each group's first control). Built-in settings are not reset and keep working — only the UI changes; together with `anti_aim` / `ui.set_setting` a script can replace AA completely. Unload, a load error or `ui.restore_tab('AA')` bring the tab back. One tab is held by one script (`ui.is_tab_overridden(tab)`); Config / Cloud / Admin cannot be replaced. `ui.set_group(id, group, tab)` binds a control to a specific tab when the script replaces several; controls without a tab go to the first replaced one. The gamesense path `ui.new_*('AA', 'Anti-aimbot angles', 'Name')` sets the tab and group directly. Controls that do not land in a replaced tab stay in Config > Lua.

`ui.reset_setting(key)` releases this script's override. Unload restores the previous script owner or the user's base value; user changes observed between calls become the new base. For a standalone AA builder use the `anti_aim` command fields. `AA.desync`, `AA.desyncAmount`, `AA.yawModifier`, `AA.modifierRange` also expose the built-in mechanisms.

## Drawing

Screen coordinates in pixels, colors RGBA 0…255; alpha 255 is opaque. Only inside `paint`:

```lua
renderer.text(x,y,r,g,b,a,text,size) -- Code font, size 8…48
renderer.rectangle(x,y,w,h,r,g,b,a)
renderer.line(x1,y1,x2,y2,r,g,b,a,thickness)
renderer.circle(x,y,radius,r,g,b,a,filled)
renderer.gradient(x,y,w,h,r,g,b,a,r2,g2,b2,a2,horizontal)
local x,y = renderer.world_to_screen(worldX,worldY,worldZ)
```

World-to-screen takes Source hu, 12 hu = 1 stud, and returns nil off screen. Drawings reuse pooled GUI objects and sit below the menu. The pool is separate per Frame / TextLabel / ImageLabel: changing the number of lines does not recreate the text and images after them. The cache holds at most 384 objects of each of these three classes (1152 in total), but the limit of active drawings stays 384 per frame. Unused elements are hidden; unload / error deletes the cache. Combine primitives for outlines, shadows, glow, indicators and animations.

More graphics:

```lua
renderer.rounded_rectangle(x,y,w,h,r,g,b,a,radius,corners) -- corners: 'left', 'tr', 'top', 'tl bl'... (the rest stay square)
renderer.rounded_outline(x,y,w,h,r,g,b,a,radius,thickness) -- outline inside the rect, like ImGui AddRect
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

Fonts: `code`, `ui`, `ui_bold`, `gotham`. Align: left / center / right. Polyline up to 64 points, arc up to 64 segments, clip nesting 8 / 16 clips per frame. Every generated primitive counts against the 384 draws. Filled triangles use two pooled right-triangle images and lazily allocate two 64x64 masks (32 KiB), counted in the script's texture quota and freed on unload. Ordinary label updates change the text directly, without rebuilding the whole Lua menu.

## 3D bullet tracers

`renderer.tracer(fromVector, toVector, options?)` creates a real client-side Roblox Beam and returns a private numeric handle. Call it once in `shot`, not every `paint`. Endpoints and widths use Source hu (12 hu = 1 stud). The beam stays in world space and uses normal engine depth testing against opaque geometry; it does not draw through walls. No Instances are exposed and effects never affect collision, ray queries or the server simulation.

```lua
local id = renderer.tracer(e.start, e.impact, {
    color={125,209,255,255}, width=2, end_width=.5,
    life=1, fade=.3, glow=1,
    texture='', texture_speed=0, texture_length=12,
})
renderer.remove_tracer(id) -- true if removed, false if already expired
renderer.clear_tracers() -- this script only
```

Options: RGBA color; start / end widths .05..24 hu; life .05..10 seconds; fade = the final 0..life seconds; glow 0..1 is Beam.LightEmission (not a bloom guarantee). The optional texture accepts an `rbxassetid://` image ID available to this experience, not an embedded PNG handle or an HTTP URL; texture speed -20..20, texture length .1..256 hu. Asset permissions still apply. Defaults: warm white, width 1 hu, life 1 s, fade .3 s, glow .5, no texture. A straight camera-facing ribbon, not a cylindrical mesh. Maximum length 16384 hu, 64 simultaneous / 16 new tracers per script per rendered frame. Expiry, unload, reload and script errors remove the effects. Ready-to-run example: `lua-examples/bullet-tracers.lua` (your own confirmed shots by default; other players optional).

`through_walls=true` draws the tracer over the map: a plain line of constant thickness, `width` is then in pixels (1..10), no texture / glow / `end_width`. `renderer.effect` takes the same option for `sphere`, `box` (flat color, no material) and `text`.

## Images inside Lua

A PNG can be embedded right in the source as a string `"\x89\x50\x4E..."` or as Base64. Images load only while the script initializes, before any events; `paint` draws an already prepared texture:

```lua
local image = renderer.load_png_base64('...Base64 PNG...')
client.set_event_callback('paint', function()
    renderer.texture(image, 20, 20, 128, 128, 255, 255, 255, 255)
end)
```

| Function | Data |
| --- | --- |
| `renderer.load_png(bytes)` | Binary PNG string, including a `\xNN` literal. |
| `renderer.load_png_base64(text)` | Standard Base64; whitespace / line breaks and a `data:image/png;base64,` prefix are allowed. |
| `renderer.load_rgba(bytes,w,h)` | Binary string of exactly `w*h*4` bytes, RGBA order, rows top to bottom. |
| `renderer.load_rgba_base64(text,w,h)` | The same RGBA pixels in Base64. |
| `renderer.texture(id,x,y,w,h,r,g,b,a[,sx,sy,sw,sh])` | Draws scaled, with a color multiplier and overall alpha. White keeps the original colors. Optional `sx,sy,sw,sh` draws only that pixel rectangle of the texture (atlases, sprite sheets). |
| `renderer.texture_size(id)` | Original `width,height`. |
| `renderer.free_texture(id)` | Frees the image and its quota; the handle cannot be used afterwards. |

Loaders return a numeric handle private to the current script. Supported: 8-bit-per-channel PNG — RGB, RGBA, grayscale, grayscale + alpha; palettes of 1/2/4/8 bits, `tRNS`, all five filters, stored / fixed / dynamic DEFLATE. PNG CRC and zlib Adler checksums are verified. Interlaced / 16-bit PNGs must be re-exported as plain non-interlaced 8-bit PNGs; JPEG / SVG are not supported yet. The optional sizes in `load_png(bytes,w,h)` must match the PNG; scaling is set in `texture`.

Limits: source image up to **1024×1024**, binary PNG up to **512 KiB**, up to **32 textures / 1 MiB of RGBA pixels per script**. One decode is limited to about 200 ms; the total budget for successful image loads is 500 ms, after which the next load is rejected. This is separate one-time work at startup and does not use the normal 10 ms frame budget. Roblox also has its own shared EditableImage memory limit; when it runs out, the script gets a clear error and is unloaded. `Unload`, reload and errors free all textures automatically.

Ready example with a PNG and transparent RGBA pixels: `lua-examples/images.lua`. An embedded Base64 / byte string plus the code must fit into the 192 KiB source limit to be saved (up to 2 MiB to run); a large image may need a lower resolution or a more compact PNG. The PNG is not uploaded to the Roblox site and needs no HTTP; other players do not receive this local image.

## Your own fonts

Any `.ttf` / `.otf` font becomes a Lua block (a Base64 PNG atlas + a glyph table) with the kit's tool:

```
python tools/lua_font_pack.py MyFont.ttf 14 myfont.lua --name MYFONT [--chars ascii,cyrillic] [--merge icons.ttf 13 f000-f2ff]
```

Paste the block into the script, then:

```lua
local tex = renderer.load_png_base64(MYFONT_PNG)
local font = renderer.load_font(tex, MYFONT_GLYPHS, {height = MYFONT_HEIGHT})
client.set_event_callback('paint', function()
    local w = renderer.font_text(font, 20, 20, 'Hello', 255, 255, 255, 255) -- returns the width
end)
local w, h = renderer.font_measure(font, 'text')
```

`glyphs[codepoint] = {x, y, w, h, offset_x, offset_y, advance}`: the glyph's rectangle in the atlas, where its top-left sits relative to the pen (left edge, line top) and how far the pen moves. `opts.height` is the line height, `opts.fallback` the glyph code for missing characters (`?` by default). One `font_text` call = one of the 384 draws however many letters it has; unchanged text is not rebuilt. Positions snap to whole pixels (the glyphs are pixel-exact). Up to 16 fonts and 4096 glyphs per font per script, 4096 glyph objects in total. `--merge` adds an icon font (Font Awesome etc.) into the same atlas, like ImGui's MergeMode.

## Text input and avatar

```lua
client.text_input_begin('initial text') -- a hidden field takes the keyboard: any layout, paste
local text, active, cursor = client.text_input_get() -- active=false once released (Enter, click elsewhere)
client.text_input_end()
renderer.avatar(x, y, w, h, r, g, b, a, radius) -- your own player's avatar, radius = rounding
```

## Game events

The callbacks below receive copies of public data and run through the normal event queue (64 pending / up to 16 callback calls per frame). This is an API over the game's current mechanics, not the full set of Source / Roblox events. Subscribing gives no access to Instances or hidden server angles.

| Events | Data / source |
| --- | --- |
| `weapon_fire`, `bullet_impact` | A confirmed `shot`, plus `slot=shooter`, `observed=false`. Fire includes the knife; impact is bullets only. Extra victims of one penetrating bullet do not create a repeated fire / impact. |
| `player_hurt` | Confirmed shot: `slot=victim`, `attacker=shooter`, `damage`, `health`, `group`, `killed`, `start`, `impact`, `weaponId`, `cmdNumber`, `tick`, the other shot fields. Fall / bomb damage is tracked through `player_health`, without a made-up attacker. |
| `player_death` | A confirmed lethal shot with the hurt fields, or an observed transition to dead: `{slot,tick,origin,weaponId,observed=true}`. A death already seen in a snapshot is not reported again from the shot; the shot details stay in `shot` / `player_hurt`. |
| `aim_hit`, `aim_miss` | Result of your own rage shot: shot fields, `target`, `slot=aimTarget`, a `reason` string when the server has a diagnosis. Not a prediction and not a trace_bullet result. |
| `player_connect`, `player_disconnect` | `{slot,player}` from the roster. The first roster received reports players already present as connects. |
| `player_team` | `{slot,team,old_team}`. A different user in an occupied slot resets the observation of their life. |
| `player_score` | `{slot,player,previous}` when kills / deaths / assists / score change. |
| `player_spawn` | `{slot,tick,origin,weaponId,observed=true}` on the first alive snapshot or a dead → alive transition. |
| `weapon_switch`, `weapon_reload`, `weapon_reload_end` | Observed `{slot,tick,origin,weaponId,observed=true}`; switch adds `old_weaponId`. Reload_end means the reload state disappeared, including an interrupted reload. |
| `weapon_ammo` | `{slot,tick,weaponId,clip,reserve,observed=true}`. |
| `player_jump`, `player_land`, `player_scope`, `player_duck` | Transitions of public states. Common slot / tick / observed; scope adds `zoom` (only 0/1 for other players), duck adds boolean `duck`. Jump means leaving the ground, including falling off an edge. |
| `player_health`, `player_armor` | `{slot,tick,health/armor,previous,observed=true}` when that snapshot field changes; one HP change may merge several damage sources / healing / respawn. |
| `round_start`, `round_end`, `round_freeze_end`, `match_start`, `match_end` | Public match state: freeze, ended, live, start of the first round, complete respectively. |
| `round_phase` | `{phase,previous,round,tick}` when the phase changes. |
| `round_mvp` | `{mvp,round,tick}` when a round ends with an MVP. |
| `bomb_pickup`, `bomb_dropped`, `bomb_planted`, `bomb_defused`, `bomb_exploded` | `{bomb,tick,round}` on transitions of the public bomb state. |
| `bomb_state` | `{bomb,previous,tick,round}` when the state or carrier changes. |
| `bomb_beginplant`, `bomb_abortplant`, `bomb_begindefuse`, `bomb_abortdefuse` | `{slot,action,tick}`. A successful action does not report an abort; completion shows up as planted / defused. |
| `bomb_equipped` | `{slot,equipped,tick}` when the C4 is drawn / put away. |

Snapshot events describe **observed transitions**: lost or skipped intermediate states are not reconstructed. Shot / roster / match use the existing server messages; the network traffic is not extended. Check `observed` on `player_death`, and use `player_hurt` / `shot` for each hit. Events are not replayed when a Lua script is loaded mid-match.

## Controlling rage

Synchronous callbacks run in Lua load order and each gets its own copy of the table. Change the table's fields; the return value is ignored. They work only in the normal path of the built-in gun rage (not knifebot), under the shared VM budget. Numeric fields are checked for finite values / range, unknown fields are ignored. `skip=true` cannot be undone by a later script. An error / unload removes the hooks; no permanent store changes are needed.

| Callback | What you can change |
| --- | --- |
| `rage_config(c)` | Settings of one rage call: `enabled`, `autoFire`, `autoStop`, `autoScope`, `autowall`; `minDamage` 0..130, `hitchance` 0..100, `headScale` / `bodyScale` 0..100, `safe` / `body` 1..3 (Off/Prefer/Force), `fov` 0..180, `backtrack` 1..3 (Off/Last/All); `hitboxes` / `multipoint` — exactly 6 booleans: head/chest/pelvis/arms/legs/feet. `lethal` (boolean): the needed damage is the target's health instead of minDamage (the menu's "FL": the minimum damage slider at 101; then `minDamage` = 100, `lethal` = true). Read-only context `cmdNumber`, `weaponId`, `group`, `group_name`, `doubleTap`, `stopOpts`. PLAYERS overrides still apply. |
| `rage_target(t)` | `skip`, `priority`, `score` (-1e6..1e6). Context: `slot`, `health`, `origin`, `fov`. Targets are sorted priority → score → FOV. A whitelisted / dead / friendly target cannot be brought back. |
| `rage_record(r)` | `skip`, `score`; context `slot`, `tick`, `backtrack`, `origin`. Only records already valid in time; an invalid tick cannot be forced. |
| `rage_point(p)` | `skip`, `score`; context `slot`, `tick`, `backtrack`, `point`, `hitbox`, `group`, `damage`, `safe`, `center`, `fov`. Called for points that already passed world / damage / safety; score is added to the built-in rank and the record's score. Lets you choose among valid points, does not replace their coordinates. May be called many times — keep the callback short. |
| `rage_fire(s)` | `skip` — final veto of the shot after the ideal / HC checks, returning normal movement. Context `slot`, `point`, `hitbox`, `damage`, `hitchance` (lower bound), `required_hitchance`, `minDamage`, `backtrack`, `cmdNumber`. |

The normal world / damage / HC / safe checks and the server validation run after the choice. Hooks by themselves give no perfect knowledge of spread / angles and no guaranteed hit. Without active hooks the built-in choice is unchanged. Example: `lua-examples/rage-hooks.lua` (options off by default).

## Camera

`camera.get()` returns the actual `{position,pitch,yaw,roll,fov}`; position in hu, angles in degrees, FOV horizontal in the game's convention. `client.camera_position()` returns x,y,z in hu; `client.camera_angles()` still returns the player's **input** pitch,yaw.

```lua
client.set_event_callback('override_view', function(v)
    v.thirdperson=true; v.distance=100; v.fov=100
    v.position=v.position+vector.new(8,0,0)
    v.roll=5; v.collision=true
    v.viewmodel_fov=100; v.viewmodel_offset=vector.new(2,0,0)
    v.hide_viewmodel=false
end)
```

The callback is called every game render frame for a living player outside the main / team menu. Only the visual camera changes, not the usercmd, aim or server angles. Position is the camera point / thirdperson pivot in hu (the offset from the normal eye is checked first, then the thirdperson distance). Distance 0..240 hu, pitch -89..89, roll -180..180, FOV 20..150, viewmodel_fov 40..140, viewmodel_offset ±48 hu per axis in the viewmodel's local axes. `collision=true` (default) checks geometry for the offset and the distance. Death / spectator / menu cameras stay under the game's control. Settings are recomputed every frame; unload / error restores the normal camera at once. Example `lua-examples/custom-camera.lua` (off by default).

## 3D markers and effects

```lua
local id=renderer.effect('ring', position, {
    radius=8, width=.5, normal=vector.new(0,1,0),
    color={125,209,255,255}, life=1, fade=.3,
})
renderer.update_effect(id,{position=newPosition,color={255,100,100,255}})
renderer.remove_effect(id)
renderer.clear_effects()
```

Types `sphere`, `box`, `ring`, `text`, `light`, `particles`. These are local engine objects with normal depth testing, not screen drawings. Create them on an event, not again every paint; use update_effect to move them. Only your own numeric handles. Coordinates, sizes, radius / width / range and speeds are hu; time is seconds.

- Common: RGBA `color`, `life` .05..10, `fade` 0..life; `rotation` = Vector3 of angles in degrees for box / sphere. `material` neon / smooth / glass.
- Sphere: `radius` .1..240; box: positive Vector3 `size` up to 480 per axis.
- Ring: `radius`, `width` .05..24, non-zero `normal` (components ±1); 24 straight Beam segments in the normal's plane.
- Text: `text` up to 128 bytes, `text_size` 8..48; BillboardGui with `AlwaysOnTop=false`.
- Light: `brightness` 0..4, `range` 1..240; PointLight without shadows; alpha / fade change the brightness.
- Particles: a one-time burst, `count` 1..64, `speed` 0..600, `spread` 0..180, `acceleration` Vector3 up to ±1200 per axis; `radius` = particle size; optional `texture='rbxassetid://...'`, default is a built-in sparkle. Particles fade on their own over their life; the shared fade does not apply to this type.

At most 32 active effects / 16 new per render frame / 4 active lights per script. Invisible anchors take no part in collision / touch / queries. `update_effect` changes position / color / text and returns false for an expired handle; it does not extend the lifetime. Expiry, unload / reload / error remove everything. The visible glow depends on Lighting; the API does not force Bloom on. Example `lua-examples/impact-effects.lua` uses real bullet_impact / player_hurt.

## Game context

- `entity.get_local_player()` — slot number.
- `entity.get_players(enemiesOnly)` — slots from the latest public snapshots; check health / flags yourself.
- `entity.get(slot)` — copy of the public snapshot: `origin` (Vector3, hu), `yaw`, `foot`, `pitch`, `duck`, `flags`, `health`, `armor`, `weaponId`, `clip`, `reserve`, `choked`, `packetId`, `team`, `tick`, public animation layers.
- `entity.get_local_state()` — copy of the local state: `move`, `weapon`, `anim` and other simulation fields. Writing to the copy does not change the game.
- `entity.get_name(slot)`, `is_alive(slot)`, `is_enemy(slot)`, `get_origin(slot)` (x,y,z), `get_weapon(slot)` (copy of the weapon definition), `get_local_weapon()` (local held weapon definition).
- `entity.get_prop(slot,'move.weight')` reads a public snapshot path; `entity.get_history(slot,count)` returns up to 32 snapshots in chronological order, copied.
- `entity.get_hitboxes(slot,footYaw?,tick?)` returns public-pose boxes `{name,group,origin,size,radius,transform}`; transform is a CFrame value. The optional footYaw is YOUR hypothesis, not a revealed real angle. The optional tick samples public history. Up to 64 pose builds per script per frame (their time counts against the 10 ms frame budget).
- `antiaim.get_condition()` — `standing`, `moving`, `in air`, or `shared` until the state is known.
- `globals.realtime()`, `globals.curtime()` (server time), `globals.tickcount()`, `globals.frametime()`.
- `client.screen_size()`, `client.key_state('K')`, `client.log(...)`, `print(...)`.
- `client.mouse_position()`; `key_state('Mouse1'/'Mouse2')`; `client.camera_angles()` (input pitch,yaw), `client.latency()` (server latency estimate in seconds), `client.get_match()` (public match copy).
- `globals.tickinterval()` (1/64), `globals.server_tick()` (last snapshot), `globals.framecount()`.
- `vector.new(x,y,z)` — a Roblox Vector3; `buttons` — the game's button constants; `bit` — the main bit32 functions.

## Traces and target control

`client.trace_line(fromVector,toVector)` takes hu and returns `{hit,fraction,position,normal}`. Map / bullet geometry only; no player Instances. Up to 128 queries per frame per script, segments up to 8192 hu.

`client.trace_bullet(slot,fromVector,toVector,footYaw?,tick?)` traces an ideal bullet along that direction (up to the held weapon's range), using the local held weapon, the target's public pose and the normal penetration / damage rules. The optional tick samples the target's public history. Returns `{damage,hitbox,group,distance,penetrated,position}` or damage 0. It also uses one pose build; it does not sample weapon spread / HC and does not guarantee a real server hit. Real server angles remain unavailable.

```lua
rage.get_status()
rage.get_target_override(slot) -- copy of the PLAYERS adjustment
rage.set_target_override(slot, {priority=true, forceBody=true, bodyYaw=-30})
rage.reset_target_override(slot) -- release this script's overrides for the target
```

Allowed target fields: `whitelist`, `priority`, `forcePitch`, `forceBody`, `correction` (booleans), `pitch` (-89..89), `bodyYaw` (-58..58), `bodyAim` / `safePoint` (1..4, same indices as PLAYERS). Overrides are local, stacked between scripts and restored on unload / error. The target must exist in the public roster. Up to 160 override fields per script.

## Timers, state and utilities

```lua
local id = client.delay_call(1, function(value) client.log(value) end, 'hello')
local repeating = client.every(.25, function() client.log('tick') end)
client.cancel_timer(id)
storage.set('panel_x', 100)
local x = storage.get('panel_x')
storage.clear()
```

Up to 32 timers, repeating interval >= 0.05 s; no catch-up burst after a slow frame. Callbacks run as threads (see "Threads" below) and share the VM / frame budget. `storage` is private per script NAME and survives unload / reload within this game session, but it is **not cloud persistence**. Up to 64 keys / 16 KiB JSON per script; keys <= 40 bytes. Rejoining clears it.

`utils.lerp`, `clamp`, `normalize_yaw`, `angle_diff`, `smoothstep`, `json_encode`, `json_decode` (JSON up to 16 KiB).

Strings and tables (native functions run outside the VM budget, so they are bounded by size): `string.rep`, `reverse`, `format`, `split`, `table.concat` up to 4 MiB of result; `table.create` / `move` up to 1 048 576 elements; `table.sort` up to 65 536. `find`, `match`, `gmatch`, `gsub`: pattern up to 256 bytes, text up to 16 KiB; text up to 4 MiB for `find(..., true)` and for patterns that cannot backtrack (no `*`, `-`, `%b`, one `+` only at the end: `.`, `%x%x`, `[^,]+`, `%d+`). `gsub` with a function or table runs in Luau, not natively: the callback counts against the budget, and a big decoder in a thread is spread over several frames. String methods (`s:rep()`, `s:gsub()`, ...) use the same functions, and `getmetatable('').__index` is this library.

Also available: `os.clock/time/date/difftime`, `setmetatable/getmetatable` (not on tables the game handed over), `newproxy`, `rawget/rawset/rawequal/rawlen`, `_G`, `getfenv()` (the script's environment), `coroutine` (create/resume/yield/wrap/status/running/isyieldable/close, own coroutines only), `utf8`, `bit32`, `bit` (+ `tobit/tohex/arshift/rol/ror/...`), `buffer` (up to 4 MiB), `string.pack/unpack/packsize`, `math.modf/log10/frexp/ldexp/noise/cosh/sinh/tanh/map/lerp`, `collectgarbage("count")`, `debug.traceback` (a stub, no stack access). `pcall` / `xpcall` return errors like plain Lua: `error(msg, 0)` comes back exactly as `msg`, positioned errors read `name:line: message`, an error table stays a table. Budget exhaustion cannot be caught. Copies are limited to depth 5, 256 entries per table and 4096 visited values per operation.

## Threads: task, wait, auto-yield

Code whose result is not needed in this very frame runs in a thread: script loading (main chunk), event queues (`shot`, `player_hurt`, `round_start`...), timers, buttons, `gui.*` callbacks, `task.*`. When a thread uses up the frame's 10 ms it **does not fail**, it continues next frame, so heavy loading, decoding or waiting loops can be written plainly:

```lua
task.spawn(function()
    while true do
        client.log('tick')
        task.wait(1)         -- the thread sleeps 1 s, the frame is free
    end
end)
local co = task.delay(5, function(msg) client.log(msg) end, 'in 5 s')
task.cancel(co)
task.defer(function() end)   -- from the next frame
local dt, now = wait(0.5)    -- aliases: wait / spawn (= task.defer) / delay
```

Up to 64 threads per script (including waiting ones); unloading closes them all. Loading gets up to 2 s at once, then 10 ms per frame, at most 30 s of VM time in total. Callbacks the game needs in this frame (`paint`, `paint_ui`, `setup_command`, `anti_aim`, `resolve`, rage hooks, `override_view`, `shutdown`) are still aborted at the budget; `task.wait`, `readfile` before the workspace has loaded and synchronous HTTP give a clear error there (start the work with `task.spawn`). Inside a native call (a `table.sort` comparator, metamethods) a thread cannot give up the frame, so such a call is aborted too.

## load / loadstring

```lua
local f, err = loadstring('return 1 + ...', 'chunk')
print(f(2))                  -- 3
local g = load(function() return nextPiece() end)  -- reader form
```

Compiled by the same compiler into the same sandbox with the same budget. A compile error comes back as `nil, message`. Source only: bytecode (`\27...`) is refused. Up to 400 KiB per chunk, 256 chunks per script; compiling does not use the VM budget, but a long one freezes the frame.

## HTTP

```lua
-- in a thread (loading, events, task.spawn) it looks synchronous
local body = game:HttpGet('https://example.com/data.json')
local r = request({Url = 'https://api.site/x', Method = 'POST', Headers = {['Content-Type'] = 'application/json'}, Body = '{}'})
print(r.StatusCode, r.Body)            -- also r.status, r.body, r.headers, r.success
local r2 = http.get('https://example.com/')
-- in paint and the other this-frame callbacks, only with a callback:
http.get('https://example.com/', function(success, response) print(response.status) end)
http.post(url, body_or_options, callback)
http.request('PUT', url, {headers = {...}, body = '...'}, callback)
```

Also `http_request` and `syn.request`. Requests go through the game server: any `http://` / `https://` address except Roblox domains and local addresses. Before a script's first request to a new domain the player sees an Allow / Deny prompt; allowed domains are remembered, a denial lasts until rejoin. Limits: 5 at once then 30 per minute per player, 3 in flight, 8 waiting per script, 120 per minute per server; request body up to 256 KiB, response up to 1 MiB, 40 s timeout. Every new domain of a player goes to the security log. Discord webhooks are not promised (Discord blocks requests from Roblox servers).

## Files (workspace)

```lua
makefolder('mycfg')
writefile('mycfg/main.json', utils.json_encode(settings))
appendfile('log.txt', 'line\n')
if isfile('mycfg/main.json') then settings = utils.json_decode(readfile('mycfg/main.json')) end
for _, path in listfiles('mycfg') do print(path) end   -- direct children; '' = the root
delfile('log.txt'); delfolder('mycfg'); isfolder('mycfg')
```

One workspace per player, shared by all of their scripts (like executors: configs, loader caches), stored on the server, survives rejoining. Paths: letters, digits, space, `. _ - /`, up to 120 characters and 8 folders deep, no `..`. Text only (UTF-8; encode binary data, e.g. base64). Limits: 256 KiB per file, 1 MiB and 200 files in total. Reads come from the client's cache, writes are visible to scripts at once and saved by the server (at most every 30 s and on leaving). The workspace loads on join; earlier, a thread waits for it and `paint` gets an error.

## Sealed scripts

In the Lua menu: **Publish sealed** compiles the editor's source on your client without debug info (no local names, no line numbers) and sends only the bytecode to the server; the server checks it and gives an 8-character code. **Load by code**: anyone with the code runs the script, and the source never shows up (not in the menu, `print` or `load`). **My sealed scripts**, **Delete sealed (code)** list and delete your own. Publishing again under the same name keeps the code. Limits: source up to 1 MiB (a big script freezes the author's game for a few seconds, once, while publishing), 10 scripts and 2 MiB of bytecode per author, one publish per 20 s. Scripts over 400 KiB only run this way: loading by code does not compile.

### Cloud: Cloud → Show: Lua

A saved script is published from the Cloud tab (Show: Lua → Publish). **Private**: only by the code, not listed. **Public**: in the shared list with rating, downloads, search and sorting, like cloud configs. **Open source** keeps the source (up to 400 KiB): anyone can press "Save to my scripts" and get the code in Config → Lua. **Closed source** is bytecode only: from the list it can only be run. Publishing again under the same name updates the script; changing the flags removes it from the list or brings it back. One like or dislike per player, a download counts once. Public script names go through Roblox's filter, open sources are checked for blocked words. Admins can delete any public script.

## Protecting your code from copying

No Lua script can be fully protected from theft: any code that runs on the client can be dumped from memory by an executor. It can be made much harder:

- **Sealed scripts** (above): the source never leaves the author, everyone else only has bytecode without names or lines. Bytecode can be decompiled, but the result without names is hard to read.
- **An obfuscator on top**: Prometheus (presets Minify, Weak, Vmify, Medium checked; Strong has issues), luaobfuscator, MoonSec, Luraph and similar. The sandbox gives them what they usually use: `getfenv`, `newproxy`, `getmetatable('')`, `bit32`, `buffer`, `string.pack`, big strings, `pcall` errors like plain Lua.
- Best of all: obfuscate, then publish the result sealed.

## Your own resolver, AA, shot rules, keybinds

Everything below is a copy of public or your own local data; other players' real angles are never revealed.

**Resolver.** `entity.get_history(slot)` already carries the fields the built-in resolver computes for every snapshot: `resolverMax` (desync width from the public motion), `resolverJump` (sign of the last yaw jump), `resolverJitter`, `resolverPacket` (the player's packet number; its parity rides each command), `resolverCond` (1 shared, 2 standing, 3 in air, 4 moving, 5 slow walk), `resolverMovingAt` / `resolverMovingYaw` (the LBY while moving), `resolverLbyAt`, `resolverFake` (choked in the last 3 s), `resolverPrevYaw` (yaw of the previous packet), plus `lby`, `choked`, `packetId`, `move` (`strafeDir`, `strafeWeight`, `cycle`, `weight`).

```lua
resolver.get_mode()                        -- 'off' / 'default' / 'bruteforce' / 'opposite' (menu)
local foot,max=resolver.get_builtin(slot,tick?,mode?) -- the built-in resolver's feet, without Lua resolve
resolver.trusts_public(slot,tick?)         -- player without choke: public feet = real feet
resolver.is_confident(slot)                -- built-in Default is confident
resolver.get_bullets(slot,tick?)           -- enemy bullets within 32 hu of the eyes by the tick (anti-bruteforce), nil before any
resolver.fired_at(slot,tick)               -- the player fired on this tick (AA off, feet from the previous packet)
```

`resolve` may return `{foot=yaw, confident=true}`: the confidence replaces the built-in one for "Prefer safe point if unresolved". The `shot` event arrives for every shot on the server (`start`, `impact`, `group`, `victim`, `tick`), so any player's hits can test hypotheses:

```lua
-- a ray against the hitboxes only (no map, no damage): which hitbox the bullet path crosses for a hypothesis
local hit=entity.trace_hitboxes(slot,e.start,e.impact+(e.impact-e.start).Unit*64,foot,tick) -- {hitbox,group,position,distance} or nil
-- hitboxes of a free pose (your own head for another yaw / body)
local boxes=entity.build_hitboxes({origin=vector.new(x,y,z),yaw=0,foot=58,pitch=89,duck=0,weapon_id=40})
local ex,ey,ez=entity.get_eye_position(slot?) -- eyes (no slot: your own)
-- grenades in flight and active smokes (grenade mode only), hu and seconds
for _,g in entity.get_grenades() do
    -- g.id, g.type ('he'/'smoke'/'molotov'/...), g.thrower (slot), g.origin, g.velocity (Vector3), g.bounces,
    -- g.active (the smoke is already out). While flying: g.time_left (until it detonates), g.path (the predicted
    -- rest of the flight, every 4th tick + the end), g.bounce_points, g.landing (where it goes off)
end
```

The prediction is the server's own GrenadeSim against the map without players; after every bounce the server sends the exact state and the path is rebuilt. The built-in menu has the same: Visuals > Effects "Thrown grenade trajectory" (Own / Teammates / Enemies) and "Trajectory through walls".

`entity.trace_hitboxes` and `build_hitboxes` take a slot or a pose table and count against the pose limit (64 per frame).

**AnimState** — the same animation simulation the server runs (real body) and steps once per packet for the public body. Handles are private, up to 32 per script:

```lua
local a=animstate.new()
local st=animstate.step(a,{eye_yaw=yaw,velocity=vel,on_ground=true,duck=0,max_speed=230,scoped=false,dt=1/64,now=t,lby=nil,walk=false})
-- st: a copy of the state (foot, lby, maxDesync, walkToRun, velX, velZ, ...)
local b=animstate.clone(a);animstate.free(b);animstate.get(a)
animstate.start_cycle(moveYaw)             -- ANIMTAG_STARTCYCLE of the run layer for a move yaw (nil = no tag)
antiaim.get_public_state()                 -- your own public body (what others see)
```

**Shot rules.** `rage.get_last()` → `{status,target,cmd_number,firing}` of the last ragebot call (every command, not the menu's 5 Hz label); `rage.get_status()` is now the latest too. `rage.predict_damage(group,distance,armor?,weaponId?)` — CS damage for a group (`head/neck/chest/stomach/arm/leg/generic`) at a distance in hu after armor, with the held weapon or a weapon id. `exploits.get_status()` → `{double_tap='ready'|'charging'|nil,charge,max_charge,fake_duck,hide_shots}`.

**Keybinds.** `ui.get_binds()` → `{key,name,check,enabled,bind_key,mode,active}` for every menu bind (built-in and script ones) — for your own keybind list. `ui.set_bind_held(key,down)` presses / releases the bind's own key the way the touch buttons do: Hold is active while held, Toggle flips on a press (press + release), OffHotkey the other way round. Allowed for AA / Rage / Visuals / World / Misc and your own hotkeys; holds are released on unload. `ui.set_setting(key,{Key='None',Mode='Toggle'})` changes a bind's key and mode.

**Menu and HUD.** `ui.get_setting_info(key)` → `{type,min,max,integer,options,default}` (`checkbox/slider/combo/multiselect/color/hotkey/text`, combo boxes with their option names) — to rebuild a page with the same entries. `ui.set_builtin_indicators(false)` hides the left DT / DUCK / ONSHOT indicators while the script is loaded; the keybind list and watermark are Misc settings. `client.set_smoke_hidden(true)` removes grenade smoke locally (like Visuals > Effects "Remove smoke grenades"; smoke stays hidden while the menu or any script asks). `globals.render_tick()` — the fractional interpolation tick players are drawn at (`entity.get_hitboxes(slot,foot,globals.render_tick())` = the hitboxes exactly where the model is).

**Sound.** Event `player_sound` `{slot,kind,position,tick}`: another player's footstep (`step`), jump (`jump`), landing (`land`) or ladder step (`ladder`) that the client plays — for sound ESP.

## Your own menu: gui.*

A built-in widget library on native Roblox objects: the engine draws it, not the 384 `paint` primitives, so it costs the script almost nothing. Typing, scrolling, dragging and popups work by themselves. While a window is open the cursor is free and shooting, movement and the camera are held, as with the cheat menu open. Full example: `lua-examples/gui-showcase.lua`.

```lua
local win=gui.window({title='my script',subtitle='v1.0',width=680,height=480,
    theme='default',        -- 'default' / 'gamesense' / 'neverlose' or a table (below)
    key='RightShift',       -- the open / close key (default RightShift; false = none)
    follow_menu=false})     -- true: shown only together with the cheat menu (no key, no close button)
local tab=win:tab('Rage')                  -- tabs on the side or on top (theme.tabs)
local g=tab:group('Aimbot','left')         -- two columns: 'left' / 'right' (alternating by default)

local on=g:toggle('Enabled',{default=true,flag='on',bind='K',mode='Toggle'}) -- bind: an own keybind on the right
local fov=g:slider('FOV',0,180,90,{step=1,suffix='°',flag='fov'})
local box=g:dropdown('Hitbox',{'Head','Chest'},1,{flag='hb'})
local pts=g:multiselect('Points',{'Head','Chest','Legs'},{true},{flag='pts'})
local col=g:color('Color',255,90,120,255,{flag='col'})
local txt=g:textbox('Tag','hi',{placeholder='text',flag='tag'})
local key=g:keybind('Peek','X','Hold',{flag='peek'})      -- LMB: assign, RMB: mode
g:label('Any text');g:button('Run',function() gui.notify('done',{title='my script'}) end)
```

Elements: `get()`, `set(v)`, `on_change(fn)` (callback through the script's event queue, with the value), `set_visible(b)`, `set_enabled(b)`, `set_label(s)`. Values: toggle — boolean, slider — number (`step`, `format` like `'%.1f'`), dropdown — 1-based index (`set` also takes the option name, `get_option()` gives the name, `set_options(list)`), multiselect — boolean array (`get_option()` gives the selected names), color — `{Color=Color3,Alpha=0..1}` (`set` takes a Color3, `{r,g,b,a}` or `{Color,Alpha}`), textbox — a string up to 256 bytes, keybind — whether it is active (`get_key()` → key, mode; `set('K','Toggle')`). A toggle with `bind` has `is_active()` = on and its bind active. Own binds show in the menu's keybind list and behave like the built-in ones (Hold / Toggle / Always / OffHotkey).

**Linking to game settings:** `{link='Rage.doubleTap'}` (toggle), `link` on a slider (range from the setting), dropdown / multiselect (option names from the setting), color, keybind (`{link='Rage.doubleTapKey'}`), and `bind_link='...Key'` on a toggle. Such an element changes the setting the way the built-in menu does (saved in configs, not reverted on unload) and updates when the menu changes it. Allowed for AA / Rage / Visuals / World / Misc; the setting must exist (`pcall(ui.get_setting_info,key)`).

**Window:** `set_open(b)`, `is_open()`, `set_theme(t)`, `set_title(s)`, `get_position()`, `set_position(x,y)`, `set_size(w,h)`, `export()` → `{flag=value}` of flagged elements (linked ones are not included — they live in the game config), `import(t)`. To keep them across script reloads: `storage.set('menu',win:export())`.

**Themes:** a preset or a table `{preset='neverlose', accent={0,148,255}, background=..., panel=..., element=..., hover=..., border=..., text=..., subtext=..., rounding=0..16, font='gotham', title_font='gotham_bold', text_size=9..20, transparency=0..0.9, toggle='switch'|'checkbox', tabs='side'|'top'}` (colors as Color3 or `{r,g,b}`). `gui.themes()`, `gui.fonts()` list them (`gotham`, `gotham_bold`, `code`, `ui`, `ui_bold`, `roboto`, `roboto_mono`, `ubuntu`, `montserrat`, `nunito`, `arial`, `arial_bold`).

**Notifications:** `gui.notify(text,{title=...,duration=4,color={r,g,b}})` — toasts at the bottom right, up to 6.

**Your own UI on renderer:** event `input` `{kind='key'|'mouse'|'wheel',key,down,x,y,delta,typing,game}` (keys, mouse buttons, the wheel); `client.capture_input(true)` frees the cursor and holds the game's input until you pass `false`; `client.is_input_captured()`.

Limits: 4 windows, 16 tabs per window, 600 elements per script. Unloading the script removes its windows, binds and input capture.

## gamesense compatibility

gamesense forms are recognized by their arguments; the native API works as before:

- `ui.new_checkbox/slider/combobox/multiselect/color_picker/hotkey/button/label/textbox("TAB", "Group", "Name", ...)` — the menu path is dropped, the name becomes the label. Combo boxes / multiselects take their options as an argument list; for such controls `ui.get` returns the option name (multiselect: a list of names) and `ui.set` accepts names. `ui.contains(id, "Option")`. `new_hotkey(..., true)` (inline) works.
- `renderer.text(x, y, r, g, b, a, flags, max_width, ...)` — the text is joined from the arguments; flags `c` center, `r` right-aligned, `b` bold, `-` small, `+` large. `renderer.measure_text(flags, ...)`. `renderer.circle(x, y, r, g, b, a, radius, start_degrees, percentage)`, `renderer.circle_outline(..., thickness)`, `renderer.indicator(r, g, b, a, ...)` (stack on the left, returns y).
- `client.key_state(vk)` with Windows virtual key codes (`0x01` LMB, `0x41` A, `0x70` F1...), `client.color_log`, `random_int`, `random_float`, `unix_time`, `system_time`, `userid_to_entindex` (here id = slot).
- `globals.absoluteframetime`, `mapname` (`de_mirage`), `maxplayers`.
- `entity.get_prop(slot, "m_iHealth" | "m_ArmorValue" | "m_fFlags")`, `"m_vecOrigin"` returns x, y, z.
- `require "vector"`: `vector(x, y, z)` with `x/y/z` fields, operators and the methods `length`, `length2d`, `dist`, `dot`, `cross`, `normalized`, `normalize`, `angles`, `lerp`, `unpack`, `toVector3`. `vector.new(x, y, z)` still gives a Vector3. `require "bit"` = `bit`.
- `client.set_event_callback` with an unknown event (`run_command`, `net_update_start`, ...) does not crash the script: the callback is ignored, and the list of ignored events is printed after loading.

Not available: FFI, `require "gamesense/..."`, `ui.reference` by gamesense menu names (use the keys from `ui.list_settings()`), netprops other than those listed.

## Execution and limits

The text is compiled by a local LuauCeption (Luau 0.700) and the bytecode runs in Fiu. Sources are stored by the server as data and are never executed on the server. No access to the real `game` (only `game:HttpGet/HttpGetAsync/HttpPost` exist), `workspace`, `require`, the caller's environment, debug, Instances, remotes or FFI. The standard library is provided in a bounded form (see above); protected calls and coroutines keep the execution limits. Errors are shown as `line N (function): message [from line M <- ...]`.

Up to 20 saved / loaded scripts, **running and saving up to 400 KiB of source** (larger only as a sealed script, up to 1 MiB; a Roblox TextBox holds at most 200 000 bytes, a larger source is pasted in parts), **1 MiB of saved Lua in total per player**, 48 controls, 16 handlers per event, 384 drawings per frame per script. The VM budget is 10 ms per script per frame: this-frame callbacks are aborted, threads continue next frame (loading: up to 2 s at once, 30 s in total). An error or a budget overrun in a callback aborts only that call and the script keeps running; only an error while loading turns the script off. This is not hard memory isolation: the compiler and native library operations run in the same Roblox client; the VM budget does not guarantee a maximum pause for every operation.

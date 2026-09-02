// ============================================================
// The Darkroom — form-factor model  v0.3 (2026-09-01)
//
// WHAT THIS IS
// The object DARKROOM_BUILD_SPEC.md describes and BOM.md pins
// down: a self-contained translucent cube, everything in its faces,
// nothing hanging off. GEOMETRY.md is the written spec; this file is
// the model. Numbers live in BOTH and must not drift.
//
// v0.3 (2026-09-01): flush low-head screws, slot moved onto the plate below the
// screen (push-push socket behind), rear wall black-tinted, rounded button caps.
// v0.4 (2026-09-01): plate re-laid out — screen high and centred, slot pocket with a
// spherical thumb dish bottom-left, 2x2 button grid bottom-right (Select red, top-right).
//
// v0.2 REGISTER (user direction 2026-09-01): NOT the sona toy.
// Hard-edged, an old PC more than a plaything — straight faces, a
// small fillet only, visible screws on the front, no wordmark, no
// feet. Quietly cyberpunk, not over the top.
//
// ARCHITECTURE — front-loaded sled
//   SLEEVE   a 5-sided translucent box, open at the front. Thin
//            (1.8) walls around the upper light chamber, thick (3)
//            around the electronics bay, so the top glows and the
//            base stays dim. Rear wall carries the card slot and the
//            USB-C / power openings.
//   SLED     the FRONT PLATE (screen up top, slot pocket + 2x2 button
//            grid below, 4 corner screws) with a floor, a diffuser shelf and a rear
//            bulkhead hanging off its back. Every component mounts
//            on the sled. Assembly: build the sled on the bench, slide
//            it into the sleeve, drive 4 screws. Repair: 4 screws,
//            pull the whole thing out the front.
//   The rear bulkhead brings the reader slot and the PiSugar's USB-C
//   to the depth of the rear wall; the sleeve's rear openings are
//   just windows onto it.
//
// Rules kept from sona (each was a bug there): stacked cutters overlap
// by EPS; cutters that are differences get render(); PNGs stay in
// preview mode because --render drops colour; section views are a
// difference, not an intersection (intersection drops colour too).
//
// Usage — "long lens" look: OpenSCAD's perspective FOV is fixed (~60 mm equivalent),
// so render at 3x distance and 3x size, then crop the centre third. Wide 16:9 refs: --imgsize=4800,2700 dist 1150, sips -c 900 1600
// => ~180 mm equivalent. See the R_long helper in the shell history / GEOMETRY.md §5.
//   openscad -o renders/darkroom-hero.png --imgsize=4800,3600 \
//     --camera=40,42,38,62,0,32,990 --projection=p darkroom.scad && sips -c 1200 1600 renders/darkroom-hero.png
//   openscad -o renders/darkroom-glow.png ... -D 'finish="glow"' darkroom.scad
//   openscad -o renders/darkroom-rear.png --camera=40,42,38,62,0,212,330 ...
//   openscad -o renders/darkroom-exploded-tags.png --imgsize=2400,1400 \
//     --camera=34,5,40,70,0,32,700 --projection=o -D 'part="exploded_tags"' darkroom.scad
//   STL: openscad -o darkroom-sleeve.stl -D 'part="sleeve"' darkroom.scad
//        openscad -o darkroom-sled.stl   -D 'part="sled"'   darkroom.scad
// ============================================================

part   = "assembly";  // ["assembly","sleeve","sled","internals","exploded","exploded_tags","section"]
finish = "idle";      // ["idle","glow"]

EPS = 0.02;
$fn = 40;

/* ============================================================
   1. BODY — the cube
   ============================================================ */
W = 80;  D = 84;  H = 80;   // x width, y depth (front = y 0), z height
fillet    = 1.5;            // the only softening on the whole object
wall_glow = 1.8;            // upper walls + top: light escapes
wall_base = 3.0;            // lower walls + floor + rear: stays dim
face_t    = 4.0;            // front plate thickness (4 so a flush 2 mm screw head leaves 2 mm under it)
back_t    = 3.0;            // rear wall; black-tinted translucent (filament swap at 3 mm, or a bonded plate)
bay_h     = 34;             // z of the diffuser shelf: bay below, chamber above
joint_g   = 0.2;            // plate and sleeve meet flush and sharp; the hairline gap IS the joint line
joint_groove = [0, 0];      // optional perimeter groove on the plate back edge [depth, width]; 0 = off (it let the light rim show through)

/* ============================================================
   2. FRONT PLATE layout (x, z on the face)
   ============================================================ */
lcd_active = 23.4; lcd_win = lcd_active + 1.6;
lcd_bezel  = 32; lcd_bezel_deep = 0.8;
lcd_cx = W/2; lcd_cz = 55;                 // high on the face: bezel z 39..71, 9 mm top margin
lcd_pcb = [35, 1.6, 40]; lcd_glass = [27, 2.6, 29];   // x, y, z. VERIFY on the Geek Factory unit

// lower zone (z 8..32): slot pocket left, 2x2 button grid right, top edges aligned at ctl_top
ctl_top   = 32;            // shared top edge of the slot pocket and the top button row
btn_pitch = 13;            // 2x2 grid pitch (Ø10 caps, 3 mm between)
btn_cx    = [50.5, 63.5];  // grid columns
btn_cz    = [ctl_top - 5, ctl_top - 5 - btn_pitch];   // rows: 27, 14
btn_cap_d = 10; btn_cap_h = 1.4;   // cap proud of the face
btn_cap_r = 0.6;                   // roll-over on the cap's top edge (small: the flat top should fill the hole)
btn_cap_taper = 0;                 // no taper — the cap fills its cutout
btn_hole_clear = 0.3;              // hole = cap + 0.3 on diameter (0.15/side; tight for FDM, ream to fit)
// RENDER NOTE: caps are soft-touch rubber (matte, slight sheen); Select red.
btn_pos = [[btn_cx[0], btn_cz[0], "up"],     [btn_cx[1], btn_cz[0], "select"],
           [btn_cx[0], btn_cz[1], "down"],   [btn_cx[1], btn_cz[1], "power"]];   // Select = top-right, red
tact = [12, 12, 7.3];       // 12 mm tact behind each cap (BOM #4, prototype controls)

screw_inset = 5.5;         // M3 LOW-HEAD socket screws at the 4 face corners, heads FLUSH with the face
screw_head_d = 5.5; screw_head_h = 2.0; screw_cb_d = 5.9; screw_cb_deep = 2.0;   // counterbore = head height
// RENDER NOTE: screws are BLACK anodized (matte black, machined sheen on the socket edge).
post = 9;                  // square corner posts inside the sleeve the screws bite into
post_len = 14;

/* ============================================================
   3. SLED behind the plate
   ============================================================ */
sled_clear = 0.3;                              // per side, sled to sleeve
sled_w = W - 2*wall_base - 2*sled_clear;       // 73.4
sled_len = D - face_t - wall_base - sled_clear; // 77.7: plate back to just short of the rear wall
sled_floor_t = 2; sled_floor_z = wall_base + sled_clear;
bulk_t = 2;                                    // rear bulkhead
diff_t = 1.2;                                  // diffuser shelf (white)

/* ============================================================
   4. COMPONENTS — real footprints (GEOMETRY.md §4)
   ============================================================ */
pi_w = 65; pi_d = 30; pi_t = 1.4; sugar_t = 11; stack_gap = 5.5;
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 26.5], [61.5, 26.5]];
stack_x = (W - pi_w)/2;
stack_y = face_t + sled_len - bulk_t - 1 - pi_d;   // rear-biased: PiSugar edge at the bulkhead
stack_z = sled_floor_z + sled_floor_t + 1.5;        // standoffs

// microSD slot ON THE PLATE, bottom-left — the shutter (spec 1.4), part of the ritual you face.
// Push-push socket right behind the plate on a small horizontal PCB. Card 11 x 1.0.
// The slot sits centred in a recessed rounded-rectangle pocket. Below the pocket a half-disc of the
// SAME depth is cut straight in, so pocket + disc read as one flat-floored recess; the internal edge
// where the recess floor meets its wall is filleted (a straight cut, softened on the deep face).
slot_w = 12.2; slot_t = 2.0; slot_r = 0.6;      // through opening
slot_land = [26, 9, 1.5, 1.2];                  // landing pocket w, h, corner r, depth; top edge = ctl_top
slot_cx = 24.5; slot_cz = ctl_top - slot_land[1]/2;   // 27.5: slot centred in the pocket
slot_lead = 1.0;                                 // 45-degree lead-in from the pocket floor into the slot
slot_dish_r = 5.5;                               // half-disc below the pocket, centred on its bottom edge
slot_dish_cz = slot_cz - slot_land[1]/2;         // disc centre on the pocket's bottom edge
slot_recess_fillet = 0.6;                        // fillet on the floor-to-wall edge of the whole recess
sd_socket = [14.5, 15, 1.9];                     // socket body x, y(depth), z, on top of the reader PCB
reader_pcb = [24, 22, 1.6];                      // provisional, x, y, z; USB link to the Pi not modeled
// rear face (x, z): ports low, on the PiSugar edge.
usb_w = 9.4; usb_h = 3.6; usb_r = 1.6;
usb_cx = W/2 + 14; usb_cz = stack_z + 5;        // VERIFY: PiSugar 3 port height / position on its edge
pwr_d = 3.2; pwr_cx = W/2 - 14; pwr_cz = usb_cz;

px_n = 2; px_d = 5; px_pitch = 26; px_z = bay_h + diff_t + 3;

/* ============================================================
   colours
   ============================================================ */
c_sleeve = finish == "glow" ? [0.98, 0.30, 0.20, 0.88] : [0.12, 0.12, 0.13, 0.96];
// one piece: black-tinted translucent PETG, rear wall included. Reads black idle, red when the safelight is on
c_plate  = [0.17, 0.17, 0.18];       // graphite front plate — the old-PC bezel
c_sledin = [0.22, 0.22, 0.23];
c_dark   = [0.10, 0.10, 0.10];
c_glass  = [0.05, 0.05, 0.07];
c_red    = [0.82, 0.10, 0.08];
c_cap    = [0.30, 0.30, 0.31];
c_pcb    = [0.10, 0.33, 0.21];
c_sugar  = [0.15, 0.15, 0.17];
c_white  = [0.97, 0.97, 0.95];
c_led    = finish == "glow" ? [1.0, 0.25, 0.15] : [0.85, 0.85, 0.80];
c_metal  = [0.72, 0.72, 0.75];
c_screw  = [0.11, 0.11, 0.12];       // black anodized

/* ============================================================
   helpers
   ============================================================ */
module rrect(w, d, r) { hull() for (x=[r, w-r], y=[r, d-r]) translate([x,y]) circle(r=r); }
module rrect_c(w, d, r) { translate([-w/2, -d/2]) rrect(w, d, r); }
// hard block with a small fillet on every edge
module block(sz, r) { hull() for (x=[r, sz[0]-r], y=[r, sz[1]-r], z=[r, sz[2]-r]) translate([x,y,z]) sphere(r=r, $fn=20); }
// block with the y=y0 face left SHARP (the mating faces of plate and sleeve meet flush, no V-groove)
// Built as hulls (no intersection): OpenCSG preview z-fights an intersected face.
// A rounded-rect slab (fillets on the 4 long edges) at the sharp end, spheres at the filleted end.
module xz_slab(w, h, r, t) { rotate([-90,0,0]) mirror([0,0,0]) translate([0, -h, 0]) linear_extrude(t) rrect(w, h, r); }
module block_sharp_front(sz, r) { hull() { xz_slab(sz[0], sz[2], r, 0.01); for (x=[r, sz[0]-r], z=[r, sz[2]-r]) translate([x, sz[1]-r, z]) sphere(r=r, $fn=20); } }
module block_sharp_back(sz, r)  { hull() { translate([0, sz[1]-0.01, 0]) xz_slab(sz[0], sz[2], r, 0.01); for (x=[r, sz[0]-r], z=[r, sz[2]-r]) translate([x, r, z]) sphere(r=r, $fn=20); } }

/* ============================================================
   5. SLEEVE
   ============================================================ */
module sleeve_cavity() {
    // bay: thick walls
    translate([wall_base, -1, wall_base]) cube([W-2*wall_base, D - wall_base + 1, bay_h - wall_base + EPS]);
    // chamber: thick 3 mm frame for the first post_len behind the plate (posts, rim, and
    // nothing but a uniform rim visible at the joint), then thin walls (top and sides);
    // thick rear kept for the ports
    translate([wall_base, -1, bay_h]) cube([W-2*wall_base, D - wall_base + 1, H - bay_h - wall_base]);
    translate([wall_glow, face_t + post_len, bay_h]) cube([W-2*wall_glow, D - wall_base - face_t - post_len, H - bay_h - wall_glow]);
}
module rear_cuts() {
    translate([usb_cx, D + 1, usb_cz]) rotate([90,0,0]) linear_extrude(wall_base + 2) rrect_c(usb_w, usb_h, usb_r);
    translate([pwr_cx, D + 1, pwr_cz]) rotate([90,0,0]) cylinder(d=pwr_d, h=wall_base + 2);
}
module corner_posts() {   // screw bosses at the 4 inner front corners, pilot holes on the face screw pattern
    difference() {
        for (x=[wall_base - EPS, W - wall_base - post + EPS], z=[wall_base - EPS, H - wall_base - post + EPS])
            translate([x, face_t + joint_g, z]) cube([post, post_len, post]);
        for (x=[screw_inset, W-screw_inset], z=[screw_inset, H-screw_inset])
            translate([x, face_t - 1, z]) rotate([-90,0,0]) cylinder(d=2.5, h=post_len + joint_g + 2);
    }
}
module sleeve_solid() {
    difference() {
        translate([0, face_t + joint_g, 0]) block_sharp_front([W, D - face_t - joint_g, H], fillet);   // sleeve body, sharp front rim
        render() sleeve_cavity();
        rear_cuts();
    }
    corner_posts();
}

/* ============================================================
   6. SLED — front plate + floor + shelf + bulkhead
   ============================================================ */
// 2D outline of the recess in plate coords (x right, y = -z after the rotate): pocket + half-disc below it
module slot_recess_2d() { rrect_c(slot_land[0], slot_land[1], slot_land[2]); translate([0, slot_land[1]/2]) circle(r=slot_dish_r, $fn=64); }
// the recess cutter: straight walls, flat floor, fillet where floor meets wall
module slot_recess_cut() {
    d = slot_land[3]; r = slot_recess_fillet;
    translate([0,0,-1]) linear_extrude(1 + d - r + EPS) slot_recess_2d();                 // straight part
    translate([0,0,d - r]) minkowski() { linear_extrude(EPS) offset(r=-r) slot_recess_2d(); sphere(r=r, $fn=16); }   // filleted floor edge
}
module plate_cuts() {
    // screen window + shallow square bezel + glass pocket from behind
    translate([lcd_cx, -1, lcd_cz]) rotate([-90,0,0]) {
        linear_extrude(face_t + 2) rrect_c(lcd_win, lcd_win, 0.8);
        linear_extrude(1 + lcd_bezel_deep) rrect_c(lcd_bezel, lcd_bezel, 1.0);
    }
    translate([lcd_cx, face_t - lcd_glass[1] + EPS, lcd_cz]) rotate([-90,0,0])
        linear_extrude(lcd_glass[1] + 2) rrect_c(lcd_glass[0] + 0.6, lcd_glass[2] + 0.6, 0.6);
    // buttons: through holes
    for (b=btn_pos) translate([b[0], -1, b[1]]) rotate([-90,0,0]) cylinder(d=btn_cap_d + btn_hole_clear, h=face_t + 2, $fn=64);
    // the slot: recess (pocket + half-disc, flat floor, filleted floor edge), 45-degree lead-in, through opening
    translate([slot_cx, 0, slot_cz]) rotate([-90,0,0]) {
        slot_recess_cut();
        hull() {
            translate([0,0,slot_land[3] - EPS]) linear_extrude(EPS) rrect_c(slot_w + 2*slot_lead, slot_t + 2*slot_lead, slot_r + slot_lead);
            translate([0,0,slot_land[3] + slot_lead]) linear_extrude(EPS) rrect_c(slot_w, slot_t, slot_r);
        }
        translate([0,0,slot_land[3]]) linear_extrude(face_t + 2) rrect_c(slot_w, slot_t, slot_r);
    }
    // screws: counterbore + through
    for (x=[screw_inset, W-screw_inset], z=[screw_inset, H-screw_inset]) translate([x, -1, z]) rotate([-90,0,0]) {
        cylinder(d=screw_cb_d, h=1 + screw_cb_deep);
        cylinder(d=3.4, h=face_t + 2);
    }
}
module joint_groove_cut() {   // perimeter notch on the plate's back edge: the visible joint line, dark
    translate([0, face_t - joint_groove[0], 0]) difference() {
        translate([-1, 0, -1]) cube([W+2, joint_groove[0] + 1, H+2]);
        translate([joint_groove[1], -1, joint_groove[1]]) cube([W - 2*joint_groove[1], joint_groove[0] + 3, H - 2*joint_groove[1]]);
    }
}
module front_plate() { difference() { block_sharp_back([W, face_t, H], fillet); plate_cuts(); if (joint_groove[0] > 0) joint_groove_cut(); } }

module sled_frame() {
    x0 = (W - sled_w)/2;
    // lip: an inner rim behind the plate that fills the joint slit, so the
    // joint reads as a shadow line, not a see-through gap. Clears the posts.
    difference() {
        translate([wall_base + sled_clear, face_t - EPS, wall_base + sled_clear])
            cube([W - 2*wall_base - 2*sled_clear, joint_g + 1.5 + EPS, H - 2*wall_base - 2*sled_clear]);
        translate([wall_base + sled_clear + 1.5, face_t - 1, wall_base + sled_clear + 1.5])
            cube([W - 2*wall_base - 2*sled_clear - 3, joint_g + 4, H - 2*wall_base - 2*sled_clear - 3]);
        for (x=[wall_base - 1, W - wall_base - post], z=[wall_base - 1, H - wall_base - post])
            translate([x, face_t - 1, z]) cube([post + 1, joint_g + 4, post + 1]);
    }
    // floor, notched at the front corners so it clears the bottom screw posts
    difference() {
        translate([x0, face_t - EPS, sled_floor_z]) cube([sled_w, sled_len + EPS, sled_floor_t]);
        for (x=[wall_base - 1, W - wall_base - post]) translate([x, face_t - 1, 0]) cube([post + 1 + sled_clear, joint_g + post_len + 1, bay_h]);
    }
    // rear bulkhead with the port windows
    difference() {
        translate([x0, face_t + sled_len - bulk_t, sled_floor_z]) cube([sled_w, bulk_t, bay_h + 20 - sled_floor_z]);
        rear_cuts();   // same openings, so the sleeve's windows look onto real holes
    }
    // diffuser shelf rails (the white plate rests on them)
    for (x=[x0, W - x0 - 2]) translate([x, face_t - EPS, bay_h - 2]) cube([2, sled_len - bulk_t + EPS, 2]);
}
module diffuser() {
    x0 = (W - sled_w)/2;
    color(c_white) translate([x0 + 0.2, face_t + 2, bay_h]) linear_extrude(diff_t) difference() {
        square([sled_w - 0.4, sled_len - bulk_t - 2.5]);
        translate([sled_w/2 - 6, sled_len - bulk_t - 12]) rrect(12, 8, 1.5);   // cable pass-through
    }
}

/* ============================================================
   7. COMPONENTS
   ============================================================ */
module pi_stack() {
    translate([stack_x, stack_y, stack_z]) {
        color(c_sugar) cube([pi_w, pi_d, sugar_t]);
        color(c_pcb) translate([0,0,sugar_t + stack_gap]) difference() {
            cube([pi_w, pi_d, pi_t]);
            for (h=pi_holes) translate([h[0], h[1], -1]) cylinder(d=2.7, h=4);
        }
        color(c_dark) translate([3, pi_d - 5.2, sugar_t + stack_gap + pi_t]) cube([50.8, 5, 8.5]);
        color(c_metal) translate([pi_w/2 - 6, pi_d/2 - 6, sugar_t + stack_gap + pi_t]) cube([12, 12, 1.2]);
        color(c_metal) translate([usb_cx - stack_x - usb_w/2 + 0.5, pi_d - 7.5, usb_cz - stack_z - usb_h/2 + 0.5]) cube([usb_w - 1, 7.5, usb_h - 1]);
        color(c_dark)  translate([pwr_cx - stack_x - 2, pi_d - 4, pwr_cz - stack_z - 1.5]) cube([4, 4, 3]);
    }
    for (h=pi_holes) color(c_white) translate([stack_x + h[0], stack_y + h[1], sled_floor_z + sled_floor_t]) cylinder(d=4.5, h=1.5);
}
module lcd_module() {
    translate([lcd_cx - lcd_pcb[0]/2, face_t, lcd_cz - lcd_pcb[2]/2 - 2]) {
        color(c_pcb) cube(lcd_pcb);
        color(c_dark) translate([2, lcd_pcb[1], lcd_pcb[2] - 3]) cube([lcd_pcb[0] - 4, 8.5, 2.5]);
    }
    color(c_glass) translate([lcd_cx - lcd_glass[0]/2, face_t - lcd_glass[1], lcd_cz - lcd_glass[2]/2]) cube(lcd_glass);
}
module cap_profile() {           // half-section of a cap, revolved: skirt in the hole, rolled top edge
    r  = btn_cap_d/2;  rt = r - btn_cap_taper;  h = btn_cap_h + face_t - 0.4;
    hull() {
        square([r, 0.1]);                                          // skirt, full diameter, in the hole
        translate([0, h - btn_cap_r]) square([rt - btn_cap_r, btn_cap_r]);
        translate([rt - btn_cap_r, h - btn_cap_r]) circle(r=btn_cap_r, $fn=32);
        square([r, h - btn_cap_r]);                                // straight side up to the roll
    }
}
module button_cap() { rotate([-90,0,0]) mirror([0,0,1]) rotate_extrude($fn=64) cap_profile(); }
module buttons() {
    for (b=btn_pos) {
        color(b[2] == "select" ? c_red : c_cap) translate([b[0], face_t - 0.4, b[1]]) button_cap();
        color(c_dark) translate([b[0] - tact[0]/2, face_t, b[1] - tact[1]/2]) cube([tact[0], tact[2], tact[1]]);
        color(c_pcb)  translate([b[0] - 8, face_t + tact[2], b[1] - 8]) cube([16, 1.6, 16]);
    }
}
module screws() {
    for (x=[screw_inset, W-screw_inset], z=[screw_inset, H-screw_inset]) color(c_screw) translate([x, 0.02, z]) rotate([-90,0,0]) difference() {
        cylinder(d=screw_head_d, h=screw_head_h - 0.02, $fn=32);   // head flush with the face
        translate([0,0,-1]) cylinder(d=2.6, h=2.4, $fn=6);          // hex socket
    }
}
module reader_board() {   // horizontal PCB right behind the plate, push-push socket on top, mouth at the slot
    z_pcb = slot_cz - slot_t/2 - 0.3 - reader_pcb[2];
    color(c_pcb)   translate([slot_cx - reader_pcb[0]/2, face_t, z_pcb]) cube(reader_pcb);
    color(c_metal) translate([slot_cx - sd_socket[0]/2, face_t, z_pcb + reader_pcb[2]]) cube(sd_socket);
}
module safelight() {
    color(c_pcb) translate([W/2 - (px_pitch + 10)/2, D/2 - 5, bay_h + diff_t]) cube([px_pitch + 10, 10, 1.2]);
    for (i=[0:px_n-1]) color(c_led) translate([W/2 + (i-(px_n-1)/2)*px_pitch, D/2, px_z]) { cylinder(d=px_d, h=4); translate([0,0,4]) sphere(d=px_d); }
    if (finish == "glow") color([1.0, 0.35, 0.2, 0.18]) translate([W/2, D/2, bay_h + 22]) scale([1.7, 1.8, 1]) sphere(r=17, $fn=32);
}

/* ============================================================
   8. ASSEMBLY / EXPLODED
   ============================================================ */
module sleeve() {
    // one body, rear wall included — the only thing you take off is the front (sled)
    color(c_sleeve) render() sleeve_solid();
}
module sled()   { color(c_plate) front_plate(); color(c_sledin) sled_frame(); }
module internals() { pi_stack(); lcd_module(); buttons(); screws(); reader_board(); diffuser(); safelight(); }
module sled_loaded() { sled(); internals(); }

tag_rz = 32;   // must match the --camera rz so labels face the viewer
module tag(txt, at, len=10, dir=1) {
    color(c_dark) {
        translate(at) rotate([0,90,0]) cylinder(d=0.5, h=len*dir);
        translate(at + [len*dir + (dir>0 ? 2 : -2), 0, -1.2]) rotate([90,0,tag_rz])
            linear_extrude(0.3) text(txt, size=3.4, halign=(dir>0?"left":"right"), font="Helvetica");
    }
}

if (part == "assembly")  { sleeve(); sled_loaded(); }
if (part == "sleeve")    sleeve_solid();
if (part == "sled")      { front_plate(); sled_frame(); }
if (part == "internals") internals();
if (part == "section")   // cutaway at x = W/2
    difference() { union() { sleeve(); sled_loaded(); } translate([W/2, -5, -10]) cube([W, D+10, H+20]); }

if (part == "exploded" || part == "exploded_tags") {
    ey = -70;                       // the sled comes out the FRONT
    sleeve();
    translate([0, ey, 0]) { sled(); lcd_module(); buttons(); reader_board(); safelight(); }
    translate([0, ey, 0]) pi_stack();
    translate([0, ey, 14]) diffuser();                     // lifted off its rails
    translate([0, ey - 26, 0]) screws();                   // out in front of the plate
    if (part == "exploded_tags") {
        tag("sleeve: translucent PETG, open front; 1.8 walls up top, 3 below", [W+2, D/2, H - 4]);
        tag("rear wall: black-tinted, slightly translucent; USB-C + power", [W+2, D - 2, 36]);
        tag("Pi Zero 2 W over PiSugar 3; ports meet the bulkhead",          [W+2, ey + stack_y + pi_d/2, stack_z + 6]);
        tag("white diffuser shelf + 2x WS2812 above it",                   [W+2, ey + D/2 + 20, bay_h + 14 + 2]);
        tag("sled: graphite plate + floor + bulkhead; everything mounts here", [-2, ey + 1, H + 4], 10, -1);
        tag("4x M3 low-head screws, flush, into corner posts",             [-2, ey - 26, H - screw_inset], 10, -1);
        tag("2x2 buttons: Up, Select (red) / Down, Power",                  [-2, ey, btn_cz[1] - 2], 10, -1);
        tag("microSD slot in a pocket + thumb dish = the shutter; push-push socket behind", [-2, ey, slot_cz + 4], 10, -1);
        tag("1.3in ST7789 240x240 on the plate",                           [-2, ey + face_t + 2, lcd_cz], 10, -1);
    }
}

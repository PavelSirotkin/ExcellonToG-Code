"""
ExcellonToG-Code help content.
Structured data for the help window.
"""

HELP_SECTIONS = {
    "quick_start": {
        "title": "🚀 Quick Start",
        "content": [
            {"type": "title", "text": "Quick Start"},
            {"type": "paragraph", "text": "Welcome to ExcellonToG-Code! This program converts PCB drilling files into control programs for CNC machines."},

            {"type": "h2", "text": "Step 1: Loading the drill file"},
            {"type": "bullet", "text": "Click the «📂 Open Excellon (holes)» button"},
            {"type": "bullet", "text": "Choose a file with .DRL or .TXT extension"},
            {"type": "bullet", "text": "Circles of various colors will appear on the canvas — each color corresponds to a particular diameter"},
            {"type": "tip", "text": "Sample files are located in the Samples/ folder"},

            {"type": "h2", "text": "Step 2: Configure parameters"},
            {"type": "paragraph", "text": "In the «G-code Parameters» block, set:"},
            {"type": "bullet", "text": "Safe Z: height for rapid moves (typically 5 mm)"},
            {"type": "bullet", "text": "Depth: working drilling depth, NEGATIVE (e.g. -2.5 mm)"},
            {"type": "bullet", "text": "Feed: drill plunge rate (typically 100 mm/min)"},
            {"type": "warning", "text": "Important: Depth must be negative! A positive value will lift the drill upward."},

            {"type": "h2", "text": "Step 3: Generate G-code"},
            {"type": "bullet", "text": "Click «⚙ Drilling G-code»"},
            {"type": "bullet", "text": "Choose where to save the file"},
            {"type": "bullet", "text": "Done! The file can be loaded into the machine"},

            {"type": "h2", "text": "Step 4: Verification (recommended)"},
            {"type": "bullet", "text": "Click «🎬 G-code Visualization»"},
            {"type": "bullet", "text": "Check the toolpath"},
            {"type": "bullet", "text": "Use the player for step-by-step viewing"},

            {"type": "paragraph", "text": "🎉 Congratulations! You've created your first G-code!"},
        ]
    },

    "excellon_format": {
        "title": "📂 Excellon Format",
        "content": [
            {"type": "title", "text": "Excellon Format (RoundHoles)"},
            {"type": "paragraph", "text": "Excellon is a text format that describes the coordinates and diameters of round holes for CNC drilling machines. It is exported by most PCB editors (KiCad, EasyEDA, Altium, DipTrace, Eagle)."},

            {"type": "h2", "text": "File structure"},
            {"type": "bullet", "text": "Header: M48, INCH/METRIC, FMAT,2 commands"},
            {"type": "bullet", "text": "Tool descriptions: T1C0.8, T2C1.0 — diameter in mm/inches"},
            {"type": "bullet", "text": "The % command, then G90 (absolute coordinates), G05 (drilling mode)"},
            {"type": "bullet", "text": "Tool selection Tn and a sequence of X..Y.. coordinates"},
            {"type": "bullet", "text": "M30 — end of program"},

            {"type": "h2", "text": "Example"},
            {"type": "code", "text": "M48"},
            {"type": "code", "text": "METRIC,TZ"},
            {"type": "code", "text": "T1C0.8"},
            {"type": "code", "text": "T2C1.0"},
            {"type": "code", "text": "%"},
            {"type": "code", "text": "G90"},
            {"type": "code", "text": "T1"},
            {"type": "code", "text": "X10.0Y20.0"},
            {"type": "code", "text": "X15.5Y20.0"},
            {"type": "code", "text": "T2"},
            {"type": "code", "text": "X30.0Y40.0"},
            {"type": "code", "text": "M30"},

            {"type": "h2", "text": "Supported variants"},
            {"type": "bullet", "text": "Units: mm (METRIC) and inches (INCH) — inches are automatically converted to mm"},
            {"type": "bullet", "text": "Trailing zeros (TZ) and leading zeros (LZ)"},
            {"type": "bullet", "text": "Coordinate format: 2.4, 3.3, 4.2 — detected automatically"},
            {"type": "bullet", "text": "Comments after ; are ignored"},

            {"type": "tip", "text": "If a file won't open — make sure it's not SlotHoles: there coordinates come in pairs on a single line."},
        ]
    },

    "slot_format": {
        "title": "📂 SlotHoles Format",
        "content": [
            {"type": "title", "text": "SlotHoles Format (oval holes)"},
            {"type": "paragraph", "text": "SlotHoles is a variant of Excellon for describing slots (oval holes). Instead of points, line segments are specified: the start and end of each slot."},

            {"type": "h2", "text": "Format specifics"},
            {"type": "paragraph", "text": "Each slot is described by a pair of coordinates on a single line with a G85 command:"},
            {"type": "code", "text": "X10.0Y20.0G85X15.0Y20.0"},
            {"type": "paragraph", "text": "This means a slot from point (10, 20) to point (15, 20) with the milling diameter from the current Tn tool."},

            {"type": "h2", "text": "Slot processing"},
            {"type": "bullet", "text": "Slots are milled, not drilled"},
            {"type": "bullet", "text": "The mill plunges to the full depth and travels along the segment from start to end"},
            {"type": "bullet", "text": "The slot diameter equals the diameter of the Tn tool"},
            {"type": "bullet", "text": "TSP optimization picks the closer end of the slot to minimize rapid moves"},

            {"type": "h2", "text": "How to obtain"},
            {"type": "bullet", "text": "KiCad: PCB → File → Fabrication Outputs → Drill Files → Mirror Y axis OFF"},
            {"type": "bullet", "text": "EasyEDA: when exporting Gerber, two .DRL files are produced — one RoundHoles and one SlotHoles"},
            {"type": "bullet", "text": "Altium: in NC Drill settings, enable Separate drill files for plated and non-plated holes"},

            {"type": "warning", "text": "SlotHoles is a separate file! Don't try to open it via «Open Excellon» — load it through «📂 Open SlotHoles»."},
        ]
    },

    "gerber_format": {
        "title": "📂 Gerber Format",
        "content": [
            {"type": "title", "text": "Gerber Format (board outline)"},
            {"type": "paragraph", "text": "Gerber RS-274X is the standard format for describing PCB layers. In ExcellonToG-Code, Gerber is used only to load the board outline (edge-cuts) in order to obtain the trim geometry."},

            {"type": "h2", "text": "Which file is needed"},
            {"type": "bullet", "text": "edge-cuts / board outline / profile layer"},
            {"type": "bullet", "text": "Extensions: .GBR, .G, .GBP, .GKO, .GML"},
            {"type": "bullet", "text": "Typical names: *_Profile.gbr, *-Edge_Cuts.gbr, *.GKO"},

            {"type": "h2", "text": "Supported commands"},
            {"type": "bullet", "text": "%FSLAX..Y..*% — coordinate format (leading zeros, absolute)"},
            {"type": "bullet", "text": "%MOMM*% / %MOIN*% — units: mm or inches"},
            {"type": "bullet", "text": "G01 — linear interpolation"},
            {"type": "bullet", "text": "G02 / G03 — clockwise / counter-clockwise arc"},
            {"type": "bullet", "text": "G36 / G37 — region mode (closed contour, internal cutouts)"},
            {"type": "bullet", "text": "G75 — multi-quadrant arc mode (KiCad)"},
            {"type": "bullet", "text": "D01 — cut, D02 — move without cutting"},
            {"type": "bullet", "text": "M02 — end of file"},

            {"type": "h2", "text": "Automatic stroke stitching"},
            {"type": "paragraph", "text": "KiCad Edge.Cuts exports contours as separate strokes (lines and arcs). The program automatically assembles them into closed contours by connecting strokes at matching endpoints."},
            {"type": "bullet", "text": "Support for external contours and internal cutouts"},
            {"type": "bullet", "text": "Automatic contour type detection by traversal direction"},
            {"type": "bullet", "text": "Smart offset: outward for external contours, inward for internal ones"},

            {"type": "h2", "text": "What is ignored"},
            {"type": "bullet", "text": "Apertures (%ADD...*%, Dnn*) — they don't affect the outline geometry"},
            {"type": "bullet", "text": "Aperture macros, step-and-repeat, attributes"},
            {"type": "bullet", "text": "Comments (G04)"},

            {"type": "tip", "text": "The parser reads only the outline geometry — no tracks, no pads. Extras in the file won't get in the way."},

            {"type": "warning", "text": "The outline must be closed! If edge-cuts contains a gap, offset and tabs will be computed incorrectly."},
        ]
    },

    "coord_formats": {
        "title": "📂 Coordinate Formats",
        "content": [
            {"type": "title", "text": "Coordinate formats"},
            {"type": "paragraph", "text": "Excellon and Gerber can encode coordinates in different formats. The program auto-detects the format and interprets values correctly."},

            {"type": "h2", "text": "N.M notation"},
            {"type": "paragraph", "text": "N is the number of digits before the decimal point, M is after. Examples:"},
            {"type": "bullet", "text": "2.4 (2 before / 4 after): X015000 → 1.5000 mm"},
            {"type": "bullet", "text": "3.3 (3 before / 3 after): X015000 → 15.000 mm"},
            {"type": "bullet", "text": "4.2 (4 before / 2 after): X015000 → 150.00 mm"},

            {"type": "h2", "text": "Leading zeros vs Trailing zeros"},
            {"type": "bullet", "text": "LZ (Leading Zeros): leading zeros preserved, trailing ones may be missing"},
            {"type": "bullet", "text": "TZ (Trailing Zeros): trailing zeros preserved, leading ones may be missing"},

            {"type": "h2", "text": "Units"},
            {"type": "bullet", "text": "METRIC / %MOMM*% — millimeters (used directly)"},
            {"type": "bullet", "text": "INCH / %MOIN*% — inches (converted × 25.4)"},

            {"type": "h2", "text": "Auto-detection"},
            {"type": "paragraph", "text": "The parser analyzes the header (FMAT, INCH/METRIC, FSLAX..Y..) and, if necessary, the value range to choose the correct format."},

            {"type": "warning", "text": "If outline and holes come from different CAD systems and use different formats — visually verify on the canvas that everything looks correct."},

            {"type": "tip", "text": "When in doubt, open the file in a text editor and check the M48/FSLAX header."},
        ]
    },

    "param_safe_z": {
        "title": "⚙️ Safe height (safe_z)",
        "content": [
            {"type": "title", "text": "Safe height (safe_z)"},
            {"type": "paragraph", "text": "The Z height to which the tool is raised between holes and slots for rapid moves. It must be above all possible obstacles: clamps, hold-downs, board unevenness."},

            {"type": "h2", "text": "Typical values"},
            {"type": "bullet", "text": "Flat board without hold-downs: 2–5 mm"},
            {"type": "bullet", "text": "Board in standard hold-downs: 5–10 mm"},
            {"type": "bullet", "text": "Board with bulky fixtures or height differences: 10–20 mm"},

            {"type": "h2", "text": "Speed vs safety balance"},
            {"type": "paragraph", "text": "The lower safe_z is, the faster the job: less raise/lower path on each hole. But if the value is too low, the tool will hit an obstacle."},

            {"type": "tip", "text": "For boards with many holes, the difference between safe_z=5 and safe_z=20 can amount to several minutes per program."},

            {"type": "warning", "text": "If the board flexes (thick fixture, poorly clamped) — raise safe_z with a margin. Better 5 extra seconds than a broken drill."},

            {"type": "h3", "text": "Difference from park_z"},
            {"type": "paragraph", "text": "safe_z is the working height during the program. park_z is the height at the end of the program and during tool changes. park_z is usually HIGHER than safe_z for ease of drill changes."},
        ]
    },

    "param_drill_z": {
        "title": "⚙️ Drilling depth (drill_z)",
        "content": [
            {"type": "title", "text": "Drilling depth (drill_z)"},
            {"type": "paragraph", "text": "The working drilling or milling depth in millimeters. This value MUST ALWAYS be negative!"},

            {"type": "h2", "text": "Typical values"},
            {"type": "bullet", "text": "For 1.6 mm board: -1.8 mm (with 0.2 mm margin)"},
            {"type": "bullet", "text": "For 2 mm aluminum: -2.5 mm"},
            {"type": "bullet", "text": "For engraving: -0.3 to -0.5 mm"},

            {"type": "warning", "text": "Common mistake: a positive value will lift the tool UPWARD instead of plunging! Always use negative values."},

            {"type": "h2", "text": "How to calculate"},
            {"type": "paragraph", "text": "Depth = -(material thickness + margin)"},
            {"type": "paragraph", "text": "A 0.1-0.3 mm margin compensates for table unevenness and guarantees through drilling."},

            {"type": "tip", "text": "For double-sided boards, drill from both sides at half the thickness + 0.2 mm."},
        ]
    },

    "param_feed_rate": {
        "title": "⚙️ Drilling feed (feed_rate)",
        "content": [
            {"type": "title", "text": "Drilling feed (feed_rate)"},
            {"type": "paragraph", "text": "The drill plunge rate into the material along the Z axis, mm/min. Used in the G1 Z.. F.. command when entering a hole."},

            {"type": "h2", "text": "Typical values"},
            {"type": "bullet", "text": "FR-4 / fiberglass, drill 0.8–2.0 mm: 100–200 mm/min"},
            {"type": "bullet", "text": "Micro-drill 0.3–0.6 mm: 50–100 mm/min"},
            {"type": "bullet", "text": "Aluminum: 50–120 mm/min"},
            {"type": "bullet", "text": "Acrylic/Plexiglas: 80–150 mm/min"},
            {"type": "bullet", "text": "Wood: 200–500 mm/min"},

            {"type": "h2", "text": "Things to consider"},
            {"type": "bullet", "text": "Smaller drill — lower feed (micro-drills break easily)"},
            {"type": "bullet", "text": "Harder material — lower feed"},
            {"type": "bullet", "text": "Lower spindle RPM — lower feed"},

            {"type": "tip", "text": "Better to start with a conservative value (100 mm/min) and verify on 2-3 holes than to push it and break a drill on the hundredth one."},

            {"type": "warning", "text": "feed_rate is the Z (plunge) feed. For mill movement in the XY plane, mill_feed is used."},
        ]
    },

    "param_mill_feed": {
        "title": "⚙️ Milling feed (mill_feed)",
        "content": [
            {"type": "title", "text": "Milling feed (mill_feed)"},
            {"type": "paragraph", "text": "The mill movement speed in the XY plane while cutting — mm/min. Used for milling slots and cutting along the outline."},

            {"type": "h2", "text": "Typical values"},
            {"type": "bullet", "text": "FR-4, mill 1–2 mm: 150–300 mm/min"},
            {"type": "bullet", "text": "Aluminum, end mill 2 mm: 200–400 mm/min"},
            {"type": "bullet", "text": "Acrylic: 300–600 mm/min"},

            {"type": "h2", "text": "Relation to depth per pass"},
            {"type": "paragraph", "text": "If mill_feed is high but depth_per_pass is large — the mill will be overloaded. Lower one of the two: either pass depth or feed."},

            {"type": "h2", "text": "Practice"},
            {"type": "bullet", "text": "For through-cutting a board, 2–3 passes of 0.5–0.8 mm at 150–200 feed are used"},
            {"type": "bullet", "text": "For slots, usually a single full-depth pass, but with a lower feed"},

            {"type": "tip", "text": "If you hear a «squeal» from the mill — lower the feed or raise the RPM."},
        ]
    },

    "param_rapid_rate": {
        "title": "⚙️ Rapid rate (rapid_rate)",
        "content": [
            {"type": "title", "text": "Rapid rate (rapid_rate)"},
            {"type": "paragraph", "text": "The speed of rapid moves (G0) — mm/min. This is the speed at which the tool moves between holes when the mill/drill is at safe_z and not touching the material."},

            {"type": "h2", "text": "Typical values"},
            {"type": "bullet", "text": "Budget machines (GRBL, 3018): 800–1500 mm/min"},
            {"type": "bullet", "text": "Mid-range machines: 2000–3000 mm/min"},
            {"type": "bullet", "text": "Professional: 5000+ mm/min"},

            {"type": "h2", "text": "Why control rapid"},
            {"type": "paragraph", "text": "On weak machines, G0 at maximum can cause step loss (coordinate shift) or structural resonance. Lowering rapid_rate makes movements smoother at the cost of time."},

            {"type": "tip", "text": "If the machine «knocks» or loses steps on sharp turns — lower rapid_rate by 20–30%."},

            {"type": "warning", "text": "On many GRBL machines the G0 command ignores the F value entirely and uses $110/$111/$112 (max rate) from firmware. In that case rapid_rate in the G-code has no effect."},
        ]
    },

    "param_park_z": {
        "title": "⚙️ Park height (park_z)",
        "content": [
            {"type": "title", "text": "Park height (park_z)"},
            {"type": "paragraph", "text": "The Z height to which the tool is raised at the end of the program and between sections (tool change via M00). It should provide convenient access to the spindle and collet."},

            {"type": "h2", "text": "Typical values"},
            {"type": "bullet", "text": "Small desktop machines: 20–30 mm"},
            {"type": "bullet", "text": "Mid-size machines: 30–50 mm"},
            {"type": "bullet", "text": "Maximum — as far as Z travel allows"},

            {"type": "h2", "text": "Where it is used"},
            {"type": "bullet", "text": "After M00 (pause for tool change)"},
            {"type": "bullet", "text": "In the final sequence before M30 (end of program)"},
            {"type": "bullet", "text": "In combined G-code — between drilling / slot / outline sections"},

            {"type": "tip", "text": "Set park_z so you can reach the spindle by hand with a collet wrench without risk of touching the board."},

            {"type": "warning", "text": "If park_z exceeds the machine's maximum Z travel, a soft-limit alarm or a mechanical hit on the upper limit switch will occur during execution."},
        ]
    },

    "mode_simple": {
        "title": "🔧 Simple Mode",
        "content": [
            {"type": "title", "text": "Simple Mode"},
            {"type": "paragraph", "text": "Basic operating mode with a single set of parameters for all tools. Suitable for one-off tasks, simple boards, and beginners."},

            {"type": "h2", "text": "How it works"},
            {"type": "bullet", "text": "All holes are drilled with one feed and one depth"},
            {"type": "bullet", "text": "Spindle RPM is not set in the G-code (controlled manually)"},
            {"type": "bullet", "text": "M00 between tools — operator changes drills themselves"},

            {"type": "h2", "text": "When to choose"},
            {"type": "bullet", "text": "First time using the program — quick result"},
            {"type": "bullet", "text": "Board with 1–3 different hole diameters"},
            {"type": "bullet", "text": "Machine without programmable spindle control"},
            {"type": "bullet", "text": "One-off job, not worth setting up the database"},

            {"type": "h2", "text": "Limitations"},
            {"type": "bullet", "text": "Cannot set a different feed for different drills"},
            {"type": "bullet", "text": "No automatic M03 S.. (spindle RPM)"},
            {"type": "bullet", "text": "No retract at a different speed"},

            {"type": "tip", "text": "If you plan to process boards regularly — it's worth setting up «Pro» mode and the tool database once."},

            {"type": "h3", "text": "Switching"},
            {"type": "paragraph", "text": "The «Simple / Pro» switch is at the top of the interface. Switching to «Pro» reveals the «🗄 Tool Database» button."},
        ]
    },

    "mode_pro": {
        "title": "🔧 Pro Mode",
        "content": [
            {"type": "title", "text": "Pro Mode"},
            {"type": "paragraph", "text": "Extended mode with a tool database — separate parameters for each diameter. Provides full control over the machining process."},

            {"type": "h2", "text": "What it provides"},
            {"type": "bullet", "text": "Separate plunge feed (plunge_feed) for each diameter"},
            {"type": "bullet", "text": "Separate retract speed (retract_feed)"},
            {"type": "bullet", "text": "Spindle speed (spindle_speed) via M03 S.."},
            {"type": "bullet", "text": "Automatic parameter selection during generation"},

            {"type": "h2", "text": "How it works"},
            {"type": "bullet", "text": "During generation, the program looks up each diameter in the database"},
            {"type": "bullet", "text": "If the diameter is found — uses parameters from the database"},
            {"type": "bullet", "text": "If not found — shows a warning and uses global values"},

            {"type": "h2", "text": "Generated G-code structure"},
            {"type": "code", "text": "T1 M06"},
            {"type": "code", "text": "M03 S20000   ; RPM from database"},
            {"type": "code", "text": "G0 X.. Y.."},
            {"type": "code", "text": "G1 Z-1.8 F100   ; plunge from database"},
                        {"type": "code", "text": "G0 Z5 F500   ; retract from database"},

            {"type": "tip", "text": "The tool database is parameters configured once for the entire fleet of your drills and mills. After that, just pick a board and click «Generate»."},

            {"type": "warning", "text": "Make sure all diameters from the board are in the database. The «Tool X not found» warning means the program will use global values — possibly incorrect for that diameter."},
        ]
    },

    "tool_database": {
        "title": "🔧 Tool Database",
        "content": [
            {"type": "title", "text": "Tool Database"},
            {"type": "paragraph", "text": "Persistent storage of parameters for each drill and mill diameter. Stored in tool_base.json in the project root."},

            {"type": "h2", "text": "Database structure"},
            {"type": "code", "text": "{"},
            {"type": "code", "text": "  \"drills\": {"},
            {"type": "code", "text": "    \"0.8\": {"},
            {"type": "code", "text": "      \"diameter\": 0.8,"},
            {"type": "code", "text": "      \"spindle_speed\": 20000,"},
            {"type": "code", "text": "      \"plunge_feed\": 100.0,"},
            {"type": "code", "text": "      \"retract_feed\": 500.0"},
            {"type": "code", "text": "    }"},
            {"type": "code", "text": "  },"},
            {"type": "code", "text": "  \"mills\": { ... }"},
            {"type": "code", "text": "}"},

            {"type": "h2", "text": "Tool parameters"},
            {"type": "bullet", "text": "diameter — diameter in mm (also the key)"},
            {"type": "bullet", "text": "spindle_speed — RPM"},
            {"type": "bullet", "text": "plunge_feed — Z plunge feed, mm/min"},
            {"type": "bullet", "text": "retract_feed — Z retract speed, mm/min"},

            {"type": "h2", "text": "Working with the database"},
            {"type": "bullet", "text": "«🗄 Tool Database» → opens the editor"},
            {"type": "bullet", "text": "Add, delete, edit diameters"},
            {"type": "bullet", "text": "Import/export JSON for transferring between machines"},
            {"type": "bullet", "text": "Auto-fill from loaded files (add all diameters of the current project)"},

            {"type": "tip", "text": "Set up the database once for your machine/spindle and boards — and you'll never have to recall parameters for each drill again."},

            {"type": "h3", "text": "drills vs mills"},
            {"type": "paragraph", "text": "drills — drill bits (used for RoundHoles). mills — end mills (used for SlotHoles and outline cutting). The same diameter can appear in both dictionaries with different parameters."},
        ]
    },

    "outline_loading": {
        "title": "✂️ Loading the outline",
        "content": [
            {"type": "title", "text": "Loading the board outline"},
            {"type": "paragraph", "text": "The board outline is loaded from a Gerber edge-cuts (profile) file. The outline is needed for finishing cut and to verify that all holes are inside the board."},

            {"type": "h2", "text": "How to load"},
            {"type": "bullet", "text": "Click «📂 Open Board Outline (Gerber)»"},
            {"type": "bullet", "text": "Choose a .GBR / .G / .GBP / .GKO file"},
            {"type": "bullet", "text": "The outline appears on the canvas as a dark gray line"},

            {"type": "h2", "text": "Automatic contour type detection"},
            {"type": "paragraph", "text": "The program automatically determines the type of each contour (external or internal cutout) by traversal direction and applies the appropriate offset:"},
            {"type": "bullet", "text": "External contour (CCW) — offset outward for board trimming"},
            {"type": "bullet", "text": "Internal cutout (CW) — offset inward for milling holes"},
            {"type": "bullet", "text": "Support for multiple contours in a single file"},
            {"type": "bullet", "text": "Tabs are placed only on external contours"},

            {"type": "h2", "text": "Hole validation"},
            {"type": "paragraph", "text": "After loading the outline, the program checks each hole — whether it lies inside the polygon. Holes outside the outline are highlighted with red circles."},

            {"type": "bullet", "text": "Red circles = warning, but not blocking"},
            {"type": "bullet", "text": "Drilling will still be generated"},
            {"type": "bullet", "text": "The outline cut will ignore those points"},

            {"type": "h2", "text": "If the outline doesn't load"},
            {"type": "bullet", "text": "Verify that the file is actually edge-cuts (not, e.g., F.Cu)"},
            {"type": "bullet", "text": "Make sure the format is RS-274X (Gerber X), not the old RS-274D"},
            {"type": "bullet", "text": "Open the file in a text editor and look for %FSLAX..Y..*% at the beginning"},

            {"type": "tip", "text": "KiCad: Plot → Edge.Cuts → «Plot border and title block» checkbox OFF, «Use extended X2 format» is not required."},

            {"type": "warning", "text": "The outline must be CLOSED. If there is a gap in edge-cuts in the PCB editor (even microscopic), offset and tabs will be incorrect."},
        ]
    },

    "outline_params": {
        "title": "✂️ Cut parameters",
        "content": [
            {"type": "title", "text": "Outline cut parameters"},
            {"type": "paragraph", "text": "The «Outline Cut» block controls the finishing milling of the board — separating the finished PCB from the panel/blank."},

            {"type": "h2", "text": "Mill diameter (outline_tool_diameter)"},
            {"type": "bullet", "text": "Physical end mill diameter in mm"},
            {"type": "bullet", "text": "The toolpath will be offset OUTWARD by half the diameter"},
            {"type": "bullet", "text": "Typical values: 0.8 / 1.0 / 2.0 / 3.0 mm"},

            {"type": "h2", "text": "Depth per pass (depth_per_pass)"},
            {"type": "bullet", "text": "How many mm are removed in one Z pass"},
            {"type": "bullet", "text": "For 1.6 mm FR-4: 0.4–0.8 mm per pass"},
            {"type": "bullet", "text": "Smaller depth_per_pass = more passes, slower, but lower load"},
            {"type": "bullet", "text": "The program calculates the number of passes to drill_z automatically"},

            {"type": "h2", "text": "Algorithm"},
            {"type": "bullet", "text": "1. Offset the contour by the milling cutter radius outward or inward, depending on the contour type"},
            {"type": "bullet", "text": "2. Multi-pass cutting with depth_per_pass step"},
            {"type": "bullet", "text": "3. Tabs are taken into account"},

            {"type": "tip", "text": "For 1.6 mm FR-4 a good combination is: 2 mm mill, 3 passes of 0.6 mm, 150 mm/min feed."},

            {"type": "warning", "text": "The mill must be NO SMALLER than the minimum radius in the board outline, otherwise concave areas can't be offset correctly."},
        ]
    },

    "outline_tabs": {
        "title": "✂️ Holding tabs",
        "content": [
            {"type": "title", "text": "Holding tabs"},
            {"type": "paragraph", "text": "Tabs are small uncut bridges of material that hold the board in the blank after the finishing cut. After processing, tabs are broken or trimmed manually."},

            {"type": "h2", "text": "Why they are needed"},
            {"type": "bullet", "text": "Prevent the board from shifting during the last millimeters of cutting"},
            {"type": "bullet", "text": "Without tabs, the board can «fly off» or damage the mill"},
            {"type": "bullet", "text": "Allow processing several boards on a single blank"},

            {"type": "h2", "text": "Parameters"},
            {"type": "bullet", "text": "outline_n_tabs — number of tabs (typically 2–6)"},
            {"type": "bullet", "text": "outline_tab_width — bridge width along the outline (typically 2–5 mm)"},
            {"type": "bullet", "text": "outline_tab_height — bridge height, Z under-cut (typically 0.5–1.0 mm)"},

            {"type": "h2", "text": "Placement"},
            {"type": "bullet", "text": "The program places tabs strictly at the midpoints of contour sides"},
            {"type": "bullet", "text": "Never on corners — that would reduce reliability"},
            {"type": "bullet", "text": "Distributed evenly around the perimeter"},

            {"type": "h3", "text": "How a tab works"},
            {"type": "paragraph", "text": "On the final Z pass, the mill in the tab zone rises to (drill_z + tab_height), travels tab_width and lowers back. The material under the mill remains."},

            {"type": "tip", "text": "For an 80×50 mm board, 4 tabs of 2.5 mm width and 0.8 mm height are enough. The board is held reliably but breaks off easily by hand."},

            {"type": "warning", "text": "Tabs that are too wide or tall — the board is hard to separate. Too narrow/low — they may break during cutting."},
        ]
    },

    "outline_direction": {
        "title": "✂️ Direction of travel",
        "content": [
            {"type": "title", "text": "Direction of travel (CW / CCW)"},
            {"type": "paragraph", "text": "The mill's direction of movement along the board outline: CW — clockwise, CCW — counter-clockwise. The choice affects the cut type — climb or conventional."},

            {"type": "h2", "text": "Climb vs Conventional"},
            {"type": "bullet", "text": "CCW for an external outline + mill rotating clockwise = climb"},
            {"type": "bullet", "text": "CW for an external outline + mill clockwise = conventional"},

            {"type": "h2", "text": "Climb cutting"},
            {"type": "bullet", "text": "Better surface quality"},
            {"type": "bullet", "text": "Less mill wear"},
            {"type": "bullet", "text": "Can pull the mill toward itself with backlash"},
            {"type": "bullet", "text": "Recommended for rigid machines"},

            {"type": "h2", "text": "Conventional cutting"},
            {"type": "bullet", "text": "More stable on machines with backlash"},
            {"type": "bullet", "text": "More «fuzz» and burrs"},
            {"type": "bullet", "text": "More mill wear"},
            {"type": "bullet", "text": "Safer for budget machines (3018, DIY)"},

            {"type": "tip", "text": "Not sure? Start with CCW — that's standard climb for an external outline and gives the best board edge."},

            {"type": "warning", "text": "With clear backlash in XY axes (e.g. on a stock 3018 without modifications), climb may ruin the edge — switch to CW."},
        ]
    },

    "viz_overview": {
        "title": "🎬 Visualization overview",
        "content": [
            {"type": "title", "text": "G-code Visualization"},
            {"type": "paragraph", "text": "The 2.5D visualization window allows you to verify the generated G-code before running it on the machine. It shows the toolpath in a quasi-3D projection."},

            {"type": "h2", "text": "How to open"},
            {"type": "bullet", "text": "Click «🎬 G-code Visualization»"},
            {"type": "bullet", "text": "The button is available only after generating G-code"},
            {"type": "bullet", "text": "Loads the most recently generated file"},

            {"type": "h2", "text": "What it shows"},
            {"type": "bullet", "text": "Toolpath (all G0 and G1)"},
            {"type": "bullet", "text": "Machining depth in quasi-3D (cabinet projection)"},
            {"type": "bullet", "text": "Different colors for different tools"},
            {"type": "bullet", "text": "Tabs are highlighted in a distinct color"},

            {"type": "h2", "text": "Main window elements"},
            {"type": "bullet", "text": "Canvas with 3D toolpath"},
            {"type": "bullet", "text": "Player — playback buttons at the bottom"},
            {"type": "bullet", "text": "Legend — list of tools on the right with filters"},
            {"type": "bullet", "text": "Info panel — current command, coordinates"},

            {"type": "tip", "text": "Always check the visualization before running! Especially on unfamiliar boards or after changing parameters."},

            {"type": "h3", "text": "What to look for"},
            {"type": "bullet", "text": "Whether all holes are drilled"},
            {"type": "bullet", "text": "Tabs are at expected places (midpoints of sides)"},
            {"type": "bullet", "text": "No strange motions / «flights» through the material"},
            {"type": "bullet", "text": "The tool change sequence is reasonable"},
        ]
    },

    "viz_player": {
        "title": "🎬 Playback player",
        "content": [
            {"type": "title", "text": "Visualization player"},
            {"type": "paragraph", "text": "The player allows step-by-step playback of the G-code path at adjustable speed."},

            {"type": "h2", "text": "Controls"},
            {"type": "bullet", "text": "▶ / ⏸ — play / pause"},
            {"type": "bullet", "text": "⏮ — to the start of the program"},
            {"type": "bullet", "text": "⏭ — to the end of the program"},
            {"type": "bullet", "text": "Progress bar — frame-by-frame seeking"},
            {"type": "bullet", "text": "Speed slider — from slow to fast"},

            {"type": "h2", "text": "Useful scenarios"},
            {"type": "bullet", "text": "Slow playback — verify the operation sequence"},
            {"type": "bullet", "text": "Pause at a suspicious place — examine details"},
            {"type": "bullet", "text": "Seek to tabs — verify correct placement"},
            {"type": "bullet", "text": "Fast play — overall impression of duration"},

            {"type": "tip", "text": "Play at maximum speed — if the program completes in 2 seconds, that's a reference: real time will be many times longer, but proportions will be preserved."},
        ]
    },

    "viz_legend": {
        "title": "🎬 Tool legend",
        "content": [
            {"type": "title", "text": "Tool legend"},
            {"type": "paragraph", "text": "The legend panel to the right of the canvas shows the list of all tools used in the program and lets you control their display."},

            {"type": "h2", "text": "What is displayed"},
            {"type": "bullet", "text": "Colored tool marker"},
            {"type": "bullet", "text": "Number (T1, T2, ...) and diameter"},
            {"type": "bullet", "text": "Number of holes / path length"},
            {"type": "bullet", "text": "Visibility checkbox"},

            {"type": "h2", "text": "Actions"},
            {"type": "bullet", "text": "Click the checkbox — show / hide the tool"},
            {"type": "bullet", "text": "Double-click an entry — solo mode (only this tool)"},
            {"type": "bullet", "text": "Hover — highlight this tool's path"},

            {"type": "h2", "text": "Typical tools in the legend"},
            {"type": "bullet", "text": "Drills (T1, T2, ...) — round holes"},
            {"type": "bullet", "text": "Mill (slot) — slot milling"},
            {"type": "bullet", "text": "Outline — outline cut"},
            {"type": "bullet", "text": "Rapid — rapid moves (often listed separately)"},

            {"type": "tip", "text": "To examine a single tool in detail — use solo mode (double-click). It's easier to spot missing or extra movements."},
        ]
    },

    "viz_filters": {
        "title": "🎬 Display filtering",
        "content": [
            {"type": "title", "text": "Display filtering"},
            {"type": "paragraph", "text": "On complex programs (many tools, long path) it's useful to disable parts of the path for clarity."},

            {"type": "h2", "text": "Filtering methods"},
            {"type": "bullet", "text": "Visibility checkboxes in the legend — by tool"},
            {"type": "bullet", "text": "Solo mode — only one tool"},
            {"type": "bullet", "text": "Hide rapid moves — leave only cutting"},

            {"type": "h2", "text": "Scenarios"},
            {"type": "bullet", "text": "Check tabs only — keep outline, hide everything else"},
            {"type": "bullet", "text": "Drilling route analysis — solo mode for one drill"},
            {"type": "bullet", "text": "Rapid evaluation — hide the working part, leave rapids"},

            {"type": "tip", "text": "After filtering, double-click for auto-zoom on the remaining path."},
        ]
    },

    "viz_statistics": {
        "title": "🎬 Statistics window",
        "content": [
            {"type": "title", "text": "Project statistics window"},
            {"type": "paragraph", "text": "The enhanced statistics window provides detailed information about the project with a visually appealing data presentation."},

            {"type": "h2", "text": "How to open"},
            {"type": "bullet", "text": "Click the «📊 Statistics» button on the right panel"},
            {"type": "bullet", "text": "Available after loading Excellon and/or Gerber files"},
            {"type": "bullet", "text": "Opens in a modal window with a fixed size"},

            {"type": "h2", "text": "Information shown"},
            
            {"type": "h3", "text": "📐 Board dimensions"},
            {"type": "bullet", "text": "X and Y coordinate ranges"},
            {"type": "bullet", "text": "Board width and height in mm"},
            {"type": "bullet", "text": "Board area in cm²"},

            {"type": "h3", "text": "🔧 Tools"},
            {"type": "bullet", "text": "Holes — number of holes and drills"},
            {"type": "bullet", "text": "Slots — number of slot moves and mills"},
            {"type": "bullet", "text": "Outline cut — presence of contour and its tools"},
            {"type": "bullet", "text": "Per-tool details with diameter and count"},

            {"type": "h3", "text": "🛤️ Toolpath"},
            {"type": "bullet", "text": "Rapid (XY) — rapid moves with conversion to meters"},
            {"type": "bullet", "text": "Working (Z) — plunges and retracts"},
            {"type": "bullet", "text": "Slot milling — milling path length for oval holes"},
            {"type": "bullet", "text": "Outline milling — board cutting path length"},
            {"type": "bullet", "text": "Milling (total) — sum of slot and outline milling"},
            {"type": "bullet", "text": "Total path — total length of all moves"},

            {"type": "h3", "text": "⏱️ Processing time"},
            {"type": "bullet", "text": "Large display of total processing time"},
            {"type": "bullet", "text": "Visual progress bars for each operation type"},
            {"type": "bullet", "text": "Percentage time distribution"},
            {"type": "bullet", "text": "Breakdown: rapid, drilling, milling (slots + outline)"},

            {"type": "h2", "text": "Additional features"},
            
            {"type": "h3", "text": "📋 Copy to clipboard"},
            {"type": "bullet", "text": "«Copy» button to export data"},
            {"type": "bullet", "text": "Formatted text report"},
            {"type": "bullet", "text": "Useful for documentation and reports"},

            {"type": "h2", "text": "Color scheme"},
            {"type": "bullet", "text": "Blue (#3498DB) — rapid, X/Y dimensions, outline"},
            {"type": "bullet", "text": "Green (#27AE60) — holes, Z working travel, drilling"},
            {"type": "bullet", "text": "Red (#E74C3C) — slots, milling"},
            {"type": "bullet", "text": "Purple (#9B59B6) — area, total path"},
            {"type": "bullet", "text": "Dark blue (#2C3E50) — headings, total time"},

            {"type": "h2", "text": "Calculations"},
            {"type": "bullet", "text": "Area: (max_x - min_x) × (max_y - min_y) / 100 cm²"},
            {"type": "bullet", "text": "Time: takes into account rapid_rate, feed_rate, mill_feed"},
            {"type": "bullet", "text": "Path: sums all tool movements"},
            {"type": "bullet", "text": "Gerber support: correct outline calculation including lines and arcs"},

            {"type": "tip", "text": "Use statistics to estimate processing time and optimize parameters before running on the machine."},

            {"type": "warning", "text": "Processing time is a calculated estimate. Real time may differ due to acceleration, deceleration, and machine controller specifics."},
        ]
    },

    "viz_themes": {
        "title": "🎬 Color themes",
        "content": [
            {"type": "title", "text": "Interface color themes"},
            {"type": "paragraph", "text": "The application supports two color themes: light (default) and dark. The theme is applied to the entire interface, including canvas, controls, and windows."},

            {"type": "h2", "text": "How to switch theme"},
            {"type": "bullet", "text": "In the right settings panel, find the 'View' group"},
            {"type": "bullet", "text": "Use the toggle '☀️ Light / 🌙 Dark'"},
            {"type": "bullet", "text": "Theme is applied instantly without restarting the application"},
            {"type": "bullet", "text": "Selected theme is saved in settings and restored on next launch"},

            {"type": "h2", "text": "Light theme"},
            {"type": "bullet", "text": "Classic light interface with white background"},
            {"type": "bullet", "text": "High contrast for working in bright lighting"},
            {"type": "bullet", "text": "Used by default"},

            {"type": "h2", "text": "Dark theme"},
            {"type": "bullet", "text": "Dark background with muted colors"},
            {"type": "bullet", "text": "Reduces eye strain when working at night"},
            {"type": "bullet", "text": "All elements adapted: canvas, grid, rulers, holes, outlines"},

            {"type": "h2", "text": "What is themed"},
            {"type": "bullet", "text": "Main window and control panels"},
            {"type": "bullet", "text": "Canvas with work area, grid and rulers"},
            {"type": "bullet", "text": "Holes, slots, board outline"},
            {"type": "bullet", "text": "Dropdown lists (Combobox)"},
            {"type": "bullet", "text": "Tooltips"},
            {"type": "bullet", "text": "Statistics and visualization windows"},

            {"type": "tip", "text": "Dark theme is especially convenient for long work sessions in the evening — less eye fatigue."},

            {"type": "warning", "text": "When changing theme, all open windows (statistics, visualization) are automatically updated. If something displays incorrectly — close and reopen the window."},
        ]
    },

    "viz_localization": {
        "title": "🎬 Localization",
        "content": [
            {"type": "title", "text": "Multilingual interface"},
            {"type": "paragraph", "text": "The application supports two interface languages: Russian (default) and English. All UI elements, messages, and help are translated into both languages."},

            {"type": "h2", "text": "How to switch language"},
            {"type": "bullet", "text": "In the right settings panel, find the toggle '🌐 RU / EN'"},
            {"type": "bullet", "text": "Click to switch between Russian and English"},
            {"type": "bullet", "text": "Interface updates instantly without restart"},
            {"type": "bullet", "text": "Selected language is saved and restored on next launch"},

            {"type": "h2", "text": "What is translated"},
            {"type": "bullet", "text": "All buttons, field labels and titles"},
            {"type": "bullet", "text": "Menus and dialog windows"},
            {"type": "bullet", "text": "Tooltips"},
            {"type": "bullet", "text": "Error messages and warnings"},
            {"type": "bullet", "text": "Statistics window and text report"},
            {"type": "bullet", "text": "Help window (content and navigation)"},
            {"type": "bullet", "text": "Tool database and parameter dialogs"},
            {"type": "bullet", "text": "G-code visualization player"},

            {"type": "h2", "text": "Russian language (RU)"},
            {"type": "bullet", "text": "Default language"},
            {"type": "bullet", "text": "Full localization of all elements"},
            {"type": "bullet", "text": "Suitable for Russian-speaking users"},

            {"type": "h2", "text": "English language (EN)"},
            {"type": "bullet", "text": "Complete interface translation"},
            {"type": "bullet", "text": "Suitable for international audience"},
            {"type": "bullet", "text": "Technical terminology in English"},

            {"type": "tip", "text": "If you work in a team with foreign colleagues — English interface simplifies sharing screenshots and instructions."},

            {"type": "warning", "text": "When switching language, help content is updated automatically. If the help window was open — it will show text in the new language."},
        ]
    },

    "ui_navigation": {
        "title": "🖱️ Canvas navigation",
        "content": [
            {"type": "title", "text": "Canvas navigation"},
            {"type": "paragraph", "text": "The canvas is the work area where holes, slots and the board outline are displayed."},

            {"type": "h2", "text": "Mouse controls"},
            {"type": "bullet", "text": "Mouse wheel — zoom (in/out)"},
            {"type": "bullet", "text": "LMB + drag — pan the view"},
            {"type": "bullet", "text": "LMB double-click — auto-zoom (fit to view)"},
            {"type": "bullet", "text": "RMB on an element — tooltip with coordinates"},

            {"type": "h2", "text": "Colors and notation"},
            {"type": "bullet", "text": "Circles of different colors — holes of different diameters"},
            {"type": "bullet", "text": "Ovals — slots (oval holes)"},
            {"type": "bullet", "text": "Dark gray line — board outline"},
            {"type": "bullet", "text": "Red circles — holes outside the outline (warning)"},

            {"type": "tip", "text": "Use double-click for quick centering and zooming of all elements."},
        ]
    },

    "ui_zoom": {
        "title": "🖱️ Zoom",
        "content": [
            {"type": "title", "text": "Canvas zoom"},
            {"type": "paragraph", "text": "The canvas supports smooth zooming both for inspecting the entire board and for individual holes."},

            {"type": "h2", "text": "Zoom methods"},
            {"type": "bullet", "text": "Mouse wheel up — zoom in"},
            {"type": "bullet", "text": "Mouse wheel down — zoom out"},
            {"type": "bullet", "text": "Zoom is centered on the cursor position"},
            {"type": "bullet", "text": "LMB double-click — auto-zoom (across all elements)"},

            {"type": "h2", "text": "Behavior"},
            {"type": "bullet", "text": "Zoom is preserved when loading new files"},
            {"type": "bullet", "text": "First file load — auto-zoom"},
            {"type": "bullet", "text": "Min/max zoom is limited to reasonable values"},

            {"type": "tip", "text": "If you got lost — double-click brings the view back to the entire board."},
        ]
    },

        "ui_tooltips": {
        "title": "🖱️ Tooltips",
        "content": [
            {"type": "title", "text": "Tooltips"},
            {"type": "paragraph", "text": "The program provides two types of tooltips: contextual ones on UI elements and informational ones on canvas objects."},

            {"type": "h2", "text": "Tooltips on widgets"},
            {"type": "bullet", "text": "Hover over any button or input field"},
            {"type": "bullet", "text": "After 500 ms a tooltip with description appears"},
            {"type": "bullet", "text": "The tooltip hides when the mouse leaves or on click"},
            {"type": "bullet", "text": "The tooltip includes a reminder about F1 for full help"},

            {"type": "h2", "text": "Tooltips on canvas"},
            {"type": "bullet", "text": "RMB on a hole — coordinates and diameter"},
            {"type": "bullet", "text": "RMB on a slot — start, end, length"},
            {"type": "bullet", "text": "RMB on the outline — segment type (line / arc)"},

            {"type": "tip", "text": "Tooltips never cover the content — they appear next to the widget and disappear on any activity."},
        ]
    },

    "ui_hotkeys": {
        "title": "🖱️ Hotkeys",
        "content": [
            {"type": "title", "text": "Hotkeys"},
            {"type": "paragraph", "text": "The following hotkeys are available in the application:"},

            {"type": "h2", "text": "Main"},
            {"type": "bullet", "text": "F1 — open the help window"},

            {"type": "h2", "text": "Canvas (works when canvas has focus)"},
            {"type": "bullet", "text": "LMB double-click — auto-zoom"},
            {"type": "bullet", "text": "Mouse wheel — zoom"},
            {"type": "bullet", "text": "LMB + drag — pan"},
            {"type": "bullet", "text": "RMB — element tooltip"},

            {"type": "h2", "text": "G-code Visualization"},
            {"type": "bullet", "text": "Space — play / pause (when player has focus)"},

            {"type": "tip", "text": "F1 works from anywhere in the application — press it whenever you need help on the current step."},
        ]
    },

    "gen_drilling": {
        "title": "📊 Drilling G-code",
        "content": [
            {"type": "title", "text": "Drilling G-code"},
            {"type": "paragraph", "text": "Generates a control program only for round holes from the loaded Excellon RoundHoles file."},

            {"type": "h2", "text": "Requirements"},
            {"type": "bullet", "text": "Excellon (RoundHoles) file is loaded"},
            {"type": "bullet", "text": "G-code parameters are filled in"},

            {"type": "h2", "text": "Program structure"},
            {"type": "bullet", "text": "Header: units (G21), absolute coordinates (G90)"},
            {"type": "bullet", "text": "Block per tool: M00 pause + M03 S.. (in «Pro»)"},
            {"type": "bullet", "text": "Hole sequence: G0 XY → G1 Z → G0 Z"},
            {"type": "bullet", "text": "End: park + M05 + M30"},

            {"type": "h2", "text": "Route optimization"},
            {"type": "bullet", "text": "Holes within a single tool group are optimized via TSP"},
            {"type": "bullet", "text": "Tools are executed in the order they appear in the file"},
            {"type": "bullet", "text": "Each group's start point is the closest to (0,0) or to the previous group's end"},

            {"type": "h2", "text": "Example fragment"},
            {"type": "code", "text": "G21"},
            {"type": "code", "text": "G90"},
            {"type": "code", "text": "G0 Z5"},
            {"type": "code", "text": "T1 M06   ; diameter 0.8"},
            {"type": "code", "text": "M03 S20000"},
            {"type": "code", "text": "G0 X10.0 Y20.0"},
            {"type": "code", "text": "G1 Z-1.8 F100"},
            {"type": "code", "text": "G0 Z5"},

            {"type": "tip", "text": "For small drills (< 0.6 mm) be sure to check in the visualization that the route doesn't make unnecessary moves through the board — moves below safe_z are dangerous."},
        ]
    },

    "gen_milling": {
        "title": "📊 Milling G-code",
        "content": [
            {"type": "title", "text": "Slot milling G-code"},
            {"type": "paragraph", "text": "Generates a program only for slots (oval holes) from the Excellon SlotHoles file."},

            {"type": "h2", "text": "Requirements"},
            {"type": "bullet", "text": "SlotHoles file is loaded"},
            {"type": "bullet", "text": "G-code parameters are filled in, including mill_feed"},

            {"type": "h2", "text": "How a slot is milled"},
            {"type": "bullet", "text": "The mill is positioned at the slot's start"},
            {"type": "bullet", "text": "Plunges to drill_z with feed_rate"},
            {"type": "bullet", "text": "Linear move to the slot's end with mill_feed"},
            {"type": "bullet", "text": "Raises to safe_z, moves to the next slot"},

            {"type": "h2", "text": "Optimization specifics"},
            {"type": "paragraph", "text": "TSP for slots takes into account that a slot can be traversed in two directions. The program picks whichever end is closer to the current tool position — this minimizes rapid moves."},

            {"type": "tip", "text": "The mill diameter equals the slot diameter (taken from Tn in the file). Make sure you have a mill of the required diameter before generating."},

            {"type": "warning", "text": "The mill must be an end mill, not an ordinary drill — otherwise it will break during horizontal movement."},
        ]
    },

    "gen_outline": {
        "title": "📊 Outline G-code",
        "content": [
            {"type": "title", "text": "Outline cut G-code"},
            {"type": "paragraph", "text": "Generates only the finishing cut section based on the Gerber outline."},

            {"type": "h2", "text": "Requirements"},
            {"type": "bullet", "text": "Gerber outline is loaded"},
            {"type": "bullet", "text": "Cut parameters are filled in (mill diameter, depth per pass, tabs)"},

            {"type": "h2", "text": "What it does"},
            {"type": "bullet", "text": "Offsets the outline outward by the mill radius"},
            {"type": "bullet", "text": "Splits the cut into several Z passes"},
            {"type": "bullet", "text": "Inserts tabs at midpoints of sides on the last pass"},
            {"type": "bullet", "text": "Respects the chosen direction (CW / CCW)"},

            {"type": "h2", "text": "Structure"},
            {"type": "code", "text": "; Outline cut"},
            {"type": "code", "text": "T.. M06   ; mill diameter 2.0"},
            {"type": "code", "text": "G0 X.. Y.."},
            {"type": "code", "text": "G1 Z-0.6 F100"},
            {"type": "code", "text": "G1 X.. Y.. F150   ; pass 1"},
            {"type": "code", "text": "G1 Z-1.2"},
            {"type": "code", "text": "G1 X.. Y..        ; pass 2"},
            {"type": "code", "text": "G1 Z-1.8"},
            {"type": "code", "text": "; ... pass 3 with tabs"},

            {"type": "tip", "text": "It is recommended to run the outline cut AFTER drilling — drilled holes provide fixation points if the board is not yet glued/clamped."},
        ]
    },

    "gen_combined": {
        "title": "📊 Combined G-code",
        "content": [
            {"type": "title", "text": "Combined G-code"},
            {"type": "paragraph", "text": "A single G-code file with all operations in the proper order: drilling → slot milling → outline cut."},

            {"type": "h2", "text": "What is included"},
            {"type": "bullet", "text": "All sections from «Drilling», «Milling», «Outline» in sequence"},
            {"type": "bullet", "text": "Comment separators between sections"},
            {"type": "bullet", "text": "M00 between tool changes"},
            {"type": "bullet", "text": "park_z at the end of each section"},

            {"type": "h2", "text": "Operation order"},
            {"type": "bullet", "text": "1. Drilling (smallest to largest or by Tn order)"},
            {"type": "bullet", "text": "2. Slots (if loaded)"},
            {"type": "bullet", "text": "3. Outline cut (if Gerber is loaded)"},

            {"type": "h2", "text": "When to use"},
            {"type": "bullet", "text": "A finished board in one run"},
            {"type": "bullet", "text": "No need to edit G-code between stages"},
            {"type": "bullet", "text": "Need a single «set and forget» file"},

            {"type": "tip", "text": "In the combined file use a higher park_z — between sections the operator will be changing tools."},

            {"type": "warning", "text": "Make sure the board is securely fastened — the finishing cut will separate it from the blank!"},
        ]
    },

    "opt_tsp": {
        "title": "🔍 TSP Optimization",
        "content": [
            {"type": "title", "text": "TSP route optimization"},
            {"type": "paragraph", "text": "The Travelling Salesman Problem (TSP) is the search for the shortest path passing through all points. Used to minimize rapid moves between holes of the same tool."},

            {"type": "h2", "text": "Why it matters"},
            {"type": "bullet", "text": "Processing time depends directly on rapid path length"},
            {"type": "bullet", "text": "For 500 holes, the difference can be 2–3×"},
            {"type": "bullet", "text": "Less travel — less machine wear and less noise"},

            {"type": "h2", "text": "Algorithms used"},
            {"type": "bullet", "text": "Nearest Neighbor — fast initial heuristic"},
            {"type": "bullet", "text": "2-opt — local optimization of crossings"},

            {"type": "h2", "text": "Performance"},
            {"type": "bullet", "text": "Up to 1000 holes — solution in fractions of a second"},
            {"type": "bullet", "text": "5000 holes — a few seconds"},
            {"type": "bullet", "text": "Doesn't guarantee a global optimum, but is close to it"},

            {"type": "tip", "text": "Optimization is applied automatically — no special configuration is needed. The result is visible in the «path length» statistics field."},
        ]
    },

    "opt_nearest": {
        "title": "🔍 Nearest Neighbor",
        "content": [
            {"type": "title", "text": "Nearest Neighbor algorithm"},
            {"type": "paragraph", "text": "A simple heuristic: from the current point always go to the nearest unvisited one. Used as an initial approximation before 2-opt."},

            {"type": "h2", "text": "How it works"},
            {"type": "bullet", "text": "1. Choose a starting point"},
            {"type": "bullet", "text": "2. Find the nearest unvisited point"},
            {"type": "bullet", "text": "3. Move to it, mark as visited"},
            {"type": "bullet", "text": "4. Repeat until all are visited"},

            {"type": "h2", "text": "Characteristics"},
            {"type": "bullet", "text": "O(n²) complexity"},
            {"type": "bullet", "text": "Fast — milliseconds for thousands of points"},
            {"type": "bullet", "text": "Not optimal — can yield a route 15–25% longer than ideal"},
            {"type": "bullet", "text": "Suffers from «traps» — at the end you have to come back"},

            {"type": "h2", "text": "For slots"},
            {"type": "paragraph", "text": "A slot has two ends. When looking for the nearest slot, the algorithm checks which end is closer — milling will start from that end."},

            {"type": "tip", "text": "Nearest Neighbor is the first step. After it, 2-opt always runs to improve the route."},
        ]
    },

    "opt_2opt": {
        "title": "🔍 2-opt improvement",
        "content": [
            {"type": "title", "text": "2-opt route improvement"},
            {"type": "paragraph", "text": "Local optimization: find crossing segments in the route and «reverse» the section between them — yielding a shorter route."},

            {"type": "h2", "text": "Idea"},
            {"type": "bullet", "text": "Route A → B → ... → C → D"},
            {"type": "bullet", "text": "If d(A,C) + d(B,D) < d(A,B) + d(C,D) — reverse the B..C section"},
            {"type": "bullet", "text": "Repeat as long as improvements are found"},

            {"type": "h2", "text": "Characteristics"},
            {"type": "bullet", "text": "Improves Nearest Neighbor's result by 5–15%"},
            {"type": "bullet", "text": "Iterative — until no further improvements"},
            {"type": "bullet", "text": "O(n²) per iteration"},
            {"type": "bullet", "text": "Still a heuristic — doesn't guarantee a global optimum"},

            {"type": "h2", "text": "When it helps the most"},
            {"type": "bullet", "text": "On boards with many holes"},
            {"type": "bullet", "text": "When Nearest Neighbor «forgot» a hole in a corner"},
            {"type": "bullet", "text": "With complex layout geometry"},

            {"type": "tip", "text": "If the route length seems suspicious — check in the visualization: 2-opt usually works well, but on specific layouts it may leave non-obvious crossings."},
        ]
    },

    "trouble_file": {
        "title": "⚠️ File won't open",
        "content": [
            {"type": "title", "text": "File won't open"},
            {"type": "paragraph", "text": "Possible causes and ways to diagnose if an Excellon or Gerber file fails to load."},

            {"type": "h2", "text": "Wrong extension"},
            {"type": "bullet", "text": "Check the extension — must be .DRL / .TXT / .GBR / .G / .GBP"},
            {"type": "bullet", "text": "Renaming a file does NOT change its content — open it in a text editor and verify the format"},

            {"type": "h2", "text": "File is not Excellon"},
            {"type": "bullet", "text": "Excellon starts with M48 or directly with %, G90"},
            {"type": "bullet", "text": "If those commands aren't at the beginning — it's not Excellon"},
            {"type": "bullet", "text": "It might be: Gerber, HPGL, DXF, or just a plain text list — these need to be opened with a different button or converted"},

            {"type": "h2", "text": "The file is SlotHoles, you're opening as RoundHoles"},
            {"type": "bullet", "text": "SlotHoles contain G85 on lines with coordinates"},
            {"type": "bullet", "text": "Open it via the other button — «📂 Open SlotHoles»"},

            {"type": "h2", "text": "Corrupted file"},
            {"type": "bullet", "text": "Transfer interruption, wrong encoding"},
            {"type": "bullet", "text": "Try re-exporting from the source CAD"},

            {"type": "h2", "text": "Encoding issues"},
            {"type": "bullet", "text": "Files must be ASCII / UTF-8 without BOM"},
            {"type": "bullet", "text": "Windows-1251 and others may cause failures"},

            {"type": "tip", "text": "Open the file in Notepad++ or VSCode — the first few lines will immediately reveal the format."},
        ]
    },

    "trouble_format": {
        "title": "⚠️ Wrong format",
        "content": [
            {"type": "title", "text": "Wrong coordinate format"},
            {"type": "paragraph", "text": "The file opens, but hole coordinates look wrong — for example, the entire board is squeezed into a point or, on the contrary, stretched over kilometers."},

            {"type": "h2", "text": "Symptoms"},
            {"type": "bullet", "text": "A single point is visible on the canvas instead of the board (coordinates too large)"},
            {"type": "bullet", "text": "The board is stretched over hundreds of mm instead of the real 80×50"},
            {"type": "bullet", "text": "Hole diameters are implausible (0.0008 mm or 800 mm)"},

            {"type": "h2", "text": "Possible causes"},
            {"type": "bullet", "text": "Coordinate format N.M detected incorrectly (2.4 instead of 3.3)"},
            {"type": "bullet", "text": "Units — inches detected as mm or vice versa"},
            {"type": "bullet", "text": "The file has no explicit format declaration, auto-detection guessed wrong"},

            {"type": "h2", "text": "What to do"},
            {"type": "bullet", "text": "Open the source file in a text editor"},
            {"type": "bullet", "text": "Look for the header: FMAT, INCH/METRIC, LZ/TZ"},
            {"type": "bullet", "text": "Make sure it matches reality"},
            {"type": "bullet", "text": "If the header is incorrect — re-export from CAD with explicit format specification"},

            {"type": "tip", "text": "KiCad: Drill Files → Drill Units = Millimeters, Zeros Format = Decimal format (keep zeros). This is the most reliable option."},
        ]
    },

    "trouble_gcode": {
        "title": "⚠️ Generation errors",
        "content": [
            {"type": "title", "text": "G-code generation errors"},
            {"type": "paragraph", "text": "Typical generation problems and how to solve them."},

            {"type": "h2", "text": "Generation buttons missing"},
            {"type": "bullet", "text": "Buttons appear only after the corresponding file is loaded"},
            {"type": "bullet", "text": "No Excellon → no «Drilling G-code»"},
            {"type": "bullet", "text": "No SlotHoles → no «Milling G-code»"},
            {"type": "bullet", "text": "No Gerber → no «Outline G-code»"},

            {"type": "h2", "text": "Error: parameter is empty or invalid"},
            {"type": "bullet", "text": "Check that all required fields contain numeric values"},
            {"type": "bullet", "text": "drill_z must be negative"},
            {"type": "bullet", "text": "feed_rate, mill_feed, rapid_rate — positive"},
            {"type": "bullet", "text": "safe_z, park_z — positive"},

            {"type": "h2", "text": "Warning: tool not found in database (Pro)"},
            {"type": "bullet", "text": "In «Pro» mode each diameter must be in tool_base.json"},
            {"type": "bullet", "text": "Open «🗄 Tool Database» → «Add all» or add manually"},
            {"type": "bullet", "text": "Or temporarily switch to «Simple» mode"},

            {"type": "h2", "text": "G-code saved but doesn't work on the machine"},
            {"type": "bullet", "text": "Check that the machine supports the G-code dialect (GRBL / Mach3 / LinuxCNC)"},
            {"type": "bullet", "text": "GRBL doesn't support M06 — some firmware may reject it"},
            {"type": "bullet", "text": "Make sure machine units are mm (G21 command)"},

            {"type": "tip", "text": "Before running on the machine, ALWAYS run the program through visualization. This catches 90% of problems."},
        ]
    },

    "trouble_outline": {
        "title": "⚠️ Holes outside the outline",
        "content": [
            {"type": "title", "text": "Holes outside the outline"},
            {"type": "paragraph", "text": "After loading the Gerber outline, some holes are highlighted with red circles — meaning they are OUTSIDE the board outline."},

            {"type": "h2", "text": "Possible causes"},
            {"type": "bullet", "text": "Mismatched origin in Excellon and Gerber"},
            {"type": "bullet", "text": "Different units / coordinate formats"},
            {"type": "bullet", "text": "In the CAD, the edge-cuts outline doesn't surround all holes (layout bug)"},
            {"type": "bullet", "text": "Different orientations (mirror / rotate) between files"},

            {"type": "h2", "text": "What to do"},
            {"type": "bullet", "text": "Compare the position of the outline and holes visually — perhaps everything has shifted by the same distance"},
            {"type": "bullet", "text": "Check export settings in the CAD — origin must match for Drill and Gerber"},
            {"type": "bullet", "text": "KiCad: Auxiliary axis as origin for both Drill and Gerber"},
            {"type": "bullet", "text": "EasyEDA: when exporting, all files in one archive use the same starting point"},

            {"type": "h2", "text": "If there are only a few points"},
            {"type": "bullet", "text": "The warning doesn't block generation"},
            {"type": "bullet", "text": "Holes will simply be drilled in the air (if they're outside the blank) or in the spoilboard"},
            {"type": "bullet", "text": "Verify whether this is a real error or intentionally placed points"},

            {"type": "tip", "text": "In KiCad a useful option: «Use auxiliary axis as origin» enabled BOTH in Plot (for Gerber) AND in Drill. This guarantees coordinate alignment."},

            {"type": "warning", "text": "Don't run the outline cut until you've sorted out the red points — risk of ruining the board."},
        ]
    },

    "tips_materials": {
        "title": "💡 Material parameters",
        "content": [
            {"type": "title", "text": "Processing parameters for various materials"},
            {"type": "paragraph", "text": "Approximate parameter values for typical materials. Always tune for your machine and tool."},

            {"type": "h2", "text": "FR-4 (PCB fiberglass)"},
            {"type": "bullet", "text": "Drilling 0.8–2.0 mm: feed_rate 100–150, RPM 15000–25000"},
            {"type": "bullet", "text": "Micro drilling (0.3–0.6): feed_rate 50–80, RPM 25000+"},
            {"type": "bullet", "text": "Cutting with 2 mm mill: mill_feed 150–250, depth_per_pass 0.5–0.8"},
            
            {"type": "tip", "text": "These are guidelines! Always start with conservative values and increase gradually, listening to the machine."},

            {"type": "warning", "text": "The values listed are for budget desktop CNC machines (3018, 6040). Industrial machines allow 2–5× higher feeds."},
        ]
    },

    

        "tips_time": {
        "title": "💡 Saving time",
        "content": [
            {"type": "title", "text": "Saving processing time"},
            {"type": "paragraph", "text": "A few techniques that reduce the overall processing time without compromising quality."},

            {"type": "h2", "text": "Parameters"},
            {"type": "bullet", "text": "Reduce safe_z to the minimum safe value — reduces Z rapid travel"},
            {"type": "bullet", "text": "Increase rapid_rate to the maximum the machine can sustain"},
            {"type": "bullet", "text": "Use feed_rate at the upper bound for the material"},

            {"type": "h2", "text": "Workflow organization"},
            {"type": "bullet", "text": "Use «Combined G-code» — one board setup, one run"},
            {"type": "bullet", "text": "«Pro» mode with tool database — no time wasted setting parameters"},
            {"type": "bullet", "text": "Group several boards on a single blank (panelization)"},

            {"type": "h2", "text": "Tooling"},
            {"type": "bullet", "text": "A sharp new tool cuts faster than a dull old one"},
            {"type": "bullet", "text": "A larger mill allows a larger depth_per_pass — fewer passes"},
            {"type": "bullet", "text": "Correct RPM — faster rapid moves, more efficient cutting"},

            {"type": "h2", "text": "TSP works"},
            {"type": "paragraph", "text": "Automatic TSP optimization already minimizes rapid moves. Nothing extra needs to be done — the program takes everything into account."},

            {"type": "tip", "text": "Real example: a 100×80 board with 300 holes and outline cut — 15–20 minutes on a 3018 machine with optimized parameters."},
        ]
    },

    "about_version": {
        "title": "ℹ️ Version and license",
        "content": [
            {"type": "title", "text": "Version and license"},

            {"type": "h2", "text": "Current version"},
            {"type": "bullet", "text": "ExcellonToG-Code 5.5 (May 2026)"},

            {"type": "h2", "text": "Key changes in v5.5"},
            {"type": "bullet", "text": "🛠 Extra drilling depth (Pro) — per-tool depth override: a drill can plunge deeper than the global drill_z by a specified amount"},
            {"type": "bullet", "text": "🐛 Fixed tab shaving on first plunge — outline cut now starts in the middle of the longest non-tab segment, the cutter no longer cuts through the bridge"},
            {"type": "bullet", "text": "🔄 Changed outline cutting order — inner cutouts first, outer contour last (the board stays rigidly held by the stock during precision operations)"},

            {"type": "h2", "text": "Key changes in v5.4"},
            {"type": "bullet", "text": "✂️ Arbitrary shape contours — finishing cut now supports external contour and internal cutouts"},
            {"type": "bullet", "text": "🔍 Automatic contour type detection — program recognizes external and internal contours, applying offset outward or inward"},
            {"type": "bullet", "text": "🔧 Internal cutout milling — automatic G-code generation for cutouts within the board"},
            {"type": "bullet", "text": "🧩 KiCad Edge.Cuts support — automatic stroke stitching into closed contours"},
            {"type": "bullet", "text": "🐛 Fixed negative coordinate parsing in Gerber (arcs were displayed incorrectly)"},
            
            {"type": "h2", "text": "Key changes in v5.3"},
            {"type": "bullet", "text": "📐 Exp format support (explicit decimal point) — correct handling of KiCAD files with coordinates like X1.0Y59.0"},
            {"type": "bullet", "text": "🌐 Legend localization — replaced «tabs» with «пер.» in Russian version"},
            
            {"type": "h2", "text": "Key changes in v5.2"},
            {"type": "bullet", "text": "🔧 Root logger configuration — logging control via environment variables"},
            {"type": "bullet", "text": "🐛 LZ/TZ (zero suppression) support in Excellon parser — correct handling of KiCad/Altium files"},
            {"type": "bullet", "text": "🔧 Modal coordinates — proper handling of incomplete coordinates in Excellon"},
            {"type": "bullet", "text": "✅ Pure path validation without side effects"},
            {"type": "bullet", "text": "🔧 Parser fixes — elimination of phantom holes, stable tool sorting"},
            {"type": "bullet", "text": "📦 PyInstaller spec audit — guaranteed correct exe build"},
            
            {"type": "h2", "text": "Key changes in v5.1"},
            {"type": "bullet", "text": "🏗️ Architecture refactoring — splitting ui/app.py into modules, improved code structure"},
            {"type": "bullet", "text": "🔧 Quality improvements — full type hints, input validation, memory leak fixes"},
            {"type": "bullet", "text": "🐛 Bug fixes — file system handling, race conditions, ZeroDivisionError"},
            {"type": "bullet", "text": "🌐 Localization improvements — fixed all error messages, key deduplication"},
            
            {"type": "h2", "text": "Key changes in v5.0"},
            {"type": "bullet", "text": "🌙 Dark theme — support for light and dark color themes with instant switching"},
            {"type": "bullet", "text": "🌐 English localization — complete interface translation to English"},
            {"type": "bullet", "text": "Theming system with semantic color palettes"},
            {"type": "bullet", "text": "Automatic update of all elements when changing theme or language"},
            {"type": "bullet", "text": "Saving selected theme and language in settings"},
            {"type": "bullet", "text": "Localization of statistics, visualization windows and all dialogs"},
            {"type": "bullet", "text": "Canvas, grid, rulers adapted for both themes"},
            {"type": "bullet", "text": "Theming of tooltips and Combobox widgets"},

            {"type": "h2", "text": "Key changes in v4.7"},
            {"type": "bullet", "text": "Full-featured statistics window with detailed information about board, tools, paths and processing time"},
            {"type": "bullet", "text": "Dynamic selection of T-tool number for the outline (avoids conflicts)"},
            {"type": "bullet", "text": "Hang protection on degenerate inputs in multi-pass"},
            {"type": "bullet", "text": "Validation of contour closedness before offset and tabs operations"},
            {"type": "bullet", "text": "Iteration cap in TSP optimization for large boards"},
            {"type": "bullet", "text": "Improved parsing error handling with clear messages"},
            {"type": "bullet", "text": "Fixed tab formation in multi-pass milling"},
            {"type": "bullet", "text": "Refactoring of Z-moves into shared helpers for G-code consistency"},

            {"type": "h2", "text": "Key changes in v4.6"},
            {"type": "bullet", "text": "Built-in help system with tree navigation"},
            {"type": "bullet", "text": "Contextual tooltips on all UI elements"},
            {"type": "bullet", "text": "F1 hotkey for quick help access"},

            {"type": "h2", "text": "Key changes in v4.5"},
            {"type": "bullet", "text": "Gerber parser for the board outline"},
            {"type": "bullet", "text": "Board finishing cut with offset, tabs, multi-pass milling"},
            {"type": "bullet", "text": "polygon_ops module: offset, arc flattening, tabs, point-in-polygon"},
            {"type": "bullet", "text": "2D validation — highlighting holes outside the outline"},
            {"type": "bullet", "text": "Tabs strictly at midpoints of sides (not at corners)"},

            {"type": "h2", "text": "History"},
            {"type": "bullet", "text": "v5.5 — May 2026: Extra drilling depth (Pro), safe first plunge in outline cut, changed cutting order (inner cutouts first)"},
            {"type": "bullet", "text": "v5.4 — May 2026: Arbitrary shape contours, automatic contour type detection, KiCad stroke stitching"},
            {"type": "bullet", "text": "v5.3 — May 2026: Exp format support, legend localization"},
            {"type": "bullet", "text": "v5.2 — May 2026: Critical parser fixes, LZ/TZ support, logging"},
            {"type": "bullet", "text": "v5.1 — May 2026: Architecture refactoring, memory leak fixes"},
            {"type": "bullet", "text": "v5.0 — May 2026: Dark theme, English localization"},
            {"type": "bullet", "text": "v4.7 — Apr 2026: Full statistics, technical improvements"},
            {"type": "bullet", "text": "v4.6 — Apr 2026: Help system"},
            {"type": "bullet", "text": "v4.5 — Apr 2026: Gerber + board cut"},
            {"type": "bullet", "text": "v4.0 — Apr 2026: modular core/ui architecture, tool database, modes"},
            {"type": "bullet", "text": "v3.2 — monolithic version of 2163 lines"},

            {"type": "h2", "text": "License"},
            {"type": "paragraph", "text": "Free «ПНХ» / «PNZ» license — \"Use it in good health\". The program is free for any use — personal and commercial."},

            {"type": "paragraph", "text": "Details — in the LICENSE file and RELEASE_NOTES.md in the project root."},

            {"type": "tip", "text": "Current releases and source code: github.com/PavelSirotkin/ExcellonToG-Code"},
        ]
    },

    "about_author": {
        "title": "ℹ️ Author",
        "content": [
            {"type": "title", "text": "Author and acknowledgements"},

            {"type": "h2", "text": "Author"},
            {"type": "bullet", "text": "Pavel Sirotkin"},
            {"type": "bullet", "text": "GitHub: github.com/PavelSirotkin"},

            {"type": "h2", "text": "Feedback"},
            {"type": "paragraph", "text": "Found a bug? Have an improvement idea? Open an issue in the repository on GitHub."},

            {"type": "h2", "text": "Technologies"},
            {"type": "bullet", "text": "Python 3.8+ (pure, no numpy/scipy/shapely)"},
            {"type": "bullet", "text": "Tkinter — GUI from the standard library"},
            {"type": "bullet", "text": "pytest — for tests (248+ unit tests)"},
            {"type": "bullet", "text": "PyInstaller — exe build"},

            {"type": "h2", "text": "Project principles"},
            {"type": "bullet", "text": "Zero external runtime dependencies — runs out of the box"},
            {"type": "bullet", "text": "core / ui separation — business logic decoupled from GUI"},
            {"type": "bullet", "text": "Test coverage — critical modules under pytest"},
            {"type": "bullet", "text": "Open source code and free license"},

            {"type": "tip", "text": "The project is developed for real-world hobby CNC tasks. Priority is ease of use and «out of the box» operability."},
        ]
    },

    "about_requirements": {
        "title": "ℹ️ System requirements",
        "content": [
            {"type": "title", "text": "System requirements"},

            {"type": "h2", "text": "Python"},
            {"type": "bullet", "text": "Python 3.8 or newer (tested on 3.8–3.14)"},
            {"type": "bullet", "text": "Tkinter — included in the standard distribution"},
            {"type": "bullet", "text": "On Linux: sudo apt install python3-tk if not installed"},

            {"type": "h2", "text": "Operating system"},
            {"type": "bullet", "text": "Windows 10 / 11"},
            {"type": "bullet", "text": "Linux (tested on Ubuntu, Debian, Fedora)"},
            {"type": "bullet", "text": "macOS (10.14+)"},

            {"type": "h2", "text": "Hardware requirements"},
            {"type": "bullet", "text": "RAM: 128 MB (virtually any modern computer)"},
            {"type": "bullet", "text": "Disk: ~5 MB for sources, ~25 MB for exe build"},
            {"type": "bullet", "text": "Screen resolution: minimum 1024×768, 1366×768+ recommended"},

            {"type": "h2", "text": "Runtime dependencies"},
            {"type": "bullet", "text": "Only the Python standard library"},
            {"type": "bullet", "text": "No pip install needed to run"},

            {"type": "h2", "text": "Development dependencies (optional)"},
            {"type": "code", "text": "pytest >= 7.0"},
            {"type": "code", "text": "pytest-cov >= 4.0"},
            {"type": "paragraph", "text": "Installed via: pip install -r requirements-dev.txt"},

            {"type": "h2", "text": "Building exe (Windows, optional)"},
            {"type": "code", "text": "pip install pyinstaller"},
            {"type": "code", "text": "pyinstaller ExcellonToG-Code.spec"},

            {"type": "tip", "text": "A pre-built exe version for Windows is available in the GitHub releases — no Python installation required."},
        ]
    },
}
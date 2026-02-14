#!/bin/bash
# Build script for the potion bottle example
# Demonstrates all major GridFab CLI commands on a 32x32 sprite
# Run from the gridfab repo root: bash examples/potion/BUILD.sh

DIR="examples/potion"

# Initialize (skip if grid.txt already exists)
python -m gridfab init --size 32x32 "$DIR"

# Write palette
cat > "$DIR/palette.txt" << 'EOF'
# Potion bottle
OL=#2A2A3A
# Cork
CK=#B8864E
CL=#D4A574
# Glass
GL=#8EAADC
GD=#5B7FB5
# Liquid
LQ=#CC3333
LD=#991A1A
LL=#FF6666
# Highlight
HL=#FFFFFF
EOF

# === STEP 1: Block out shapes with rect ===
# Bottle body
python -m gridfab rect 14 11 27 20 OL --dir "$DIR"
# Neck
python -m gridfab rect 8 13 13 18 OL --dir "$DIR"
# Cork
python -m gridfab rect 6 14 8 17 OL --dir "$DIR"

# === STEP 2: Fill interiors with fill (single pixels and spans) ===
# Cork interior
python -m gridfab fill 7 15 16 CK --dir "$DIR"
python -m gridfab fill 6 15 16 CL --dir "$DIR"
# Neck glass
python -m gridfab fill 9 14 17 GL --dir "$DIR"
python -m gridfab fill 10 14 17 GL --dir "$DIR"
python -m gridfab fill 11 14 17 GL --dir "$DIR"
python -m gridfab fill 12 14 17 GL --dir "$DIR"
python -m gridfab fill 13 14 17 GL --dir "$DIR"
# Bottle body liquid (rect for the big fill)
python -m gridfab rect 15 12 26 19 LQ --dir "$DIR"
# Glass top row of body
python -m gridfab fill 14 12 19 GL --dir "$DIR"

# === STEP 3: Shading and highlights with fill (single-pixel placement) ===
# Dark liquid on right side and bottom (light source: top-left)
python -m gridfab fill 25 16 19 LD --dir "$DIR"
python -m gridfab fill 26 16 19 LD --dir "$DIR"
python -m gridfab fill 24 18 19 LD --dir "$DIR"
python -m gridfab fill 23 19 19 LD --dir "$DIR"
python -m gridfab fill 22 19 19 LD --dir "$DIR"
python -m gridfab fill 21 19 19 LD --dir "$DIR"
python -m gridfab fill 20 19 19 LD --dir "$DIR"
# Liquid highlight (top-left)
python -m gridfab fill 15 12 13 LL --dir "$DIR"
python -m gridfab fill 16 12 12 LL --dir "$DIR"
# Glass highlight on neck (top-left)
python -m gridfab fill 9 14 14 HL --dir "$DIR"
python -m gridfab fill 10 14 14 HL --dir "$DIR"
# Glass shadow on neck (right side)
python -m gridfab fill 9 17 17 GD --dir "$DIR"
python -m gridfab fill 10 17 17 GD --dir "$DIR"
python -m gridfab fill 11 17 17 GD --dir "$DIR"
python -m gridfab fill 12 17 17 GD --dir "$DIR"

# === STEP 4: Detail with row (shoulder and bottom shaping) ===
# Shoulder transition: neck widens into body
python -m gridfab row 13 . . . . . . . . . . . . OL GL GL GL GL GL OL . . . . . . . . . . . . . --dir "$DIR"
python -m gridfab row 14 . . . . . . . . . . . OL GL GL GL GL GL GL GL GL OL . . . . . . . . . . . --dir "$DIR"
# Rounded bottom
python -m gridfab row 27 . . . . . . . . . . . . OL OL OL OL OL OL OL OL OL . . . . . . . . . . . --dir "$DIR"
python -m gridfab row 28 . . . . . . . . . . . . . OL OL OL OL OL OL OL . . . . . . . . . . . . --dir "$DIR"

# === DONE: Render and export ===
python -m gridfab render "$DIR"
python -m gridfab export "$DIR"
echo "Done! Check $DIR/preview.png"

{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    poetry
    patchelf
    zlib
    glib
    fontconfig
    freetype
    xorg.libX11
    xorg.libXext
    xorg.libXrender
    xorg.libXi
    xorg.libXrandr
    xorg.libXcursor
    xorg.libXdamage
    xorg.libXfixes
    xorg.libXcomposite
    xorg.libXScrnSaver
    xorg.libXtst
    alsa-lib
    dbus
    at-spi2-core
    nspr
    nss
    expat
    libdrm
    mesa
    libxkbcommon
    atk
    pango
    cairo
    gdk-pixbuf
    gtk3
  ];

  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.glib
      pkgs.fontconfig
      pkgs.freetype
      pkgs.xorg.libX11
      pkgs.xorg.libXext
      pkgs.xorg.libXrender
      pkgs.xorg.libXi
      pkgs.xorg.libXrandr
      pkgs.xorg.libXcursor
      pkgs.xorg.libXdamage
      pkgs.xorg.libXfixes
      pkgs.xorg.libXcomposite
      pkgs.xorg.libXScrnSaver
      pkgs.xorg.libXtst
      pkgs.alsa-lib
      pkgs.dbus
      pkgs.at-spi2-core
      pkgs.nspr
      pkgs.nss
      pkgs.expat
      pkgs.libdrm
      pkgs.mesa
      pkgs.libxkbcommon
      pkgs.atk
      pkgs.pango
      pkgs.cairo
      pkgs.gdk-pixbuf
      pkgs.gtk3
    ]}:$LD_LIBRARY_PATH"

    # Automatically patch the kaleido binary interpreter if present
    KALEIDO_BIN=$(find /home/brian/.cache/pypoetry/virtualenvs/ -path "*/kaleido/executable/bin/kaleido" -print -quit 2>/dev/null)
    if [ -n "$KALEIDO_BIN" ] && [ -f "$KALEIDO_BIN" ]; then
      CURRENT_INTERP=$(patchelf --print-interpreter "$KALEIDO_BIN" 2>/dev/null)
      if [[ "$CURRENT_INTERP" == "/lib64/"* ]]; then
        echo "NixOS: Patching kaleido binary interpreter..."
        patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" "$KALEIDO_BIN"
      fi
      KALEIDO_SCRIPT="$(dirname "$KALEIDO_BIN")/../kaleido"
      if [ -f "$KALEIDO_SCRIPT" ] && grep -q "#!/bin/bash" "$KALEIDO_SCRIPT"; then
        echo "NixOS: Patching kaleido wrapper script shebang..."
        sed -i 's|#!/bin/bash|#!/usr/bin/env bash|g' "$KALEIDO_SCRIPT"
      fi
    fi
  '';
}

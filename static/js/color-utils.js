/* Paleta oficial de 36 cores e getContrastText — espelha core/colors.py.
   Qualquer mudança aqui precisa ser replicada lá também. */
(function () {
    "use strict";

    var PALETTE = [
        // Verdes
        { hex: "#84CC16", name: "Lima" },
        { hex: "#22C55E", name: "Verde" },
        { hex: "#16A34A", name: "Verde escuro" },
        { hex: "#10B981", name: "Esmeralda" },
        { hex: "#14B8A6", name: "Turquesa" },
        { hex: "#0F766E", name: "Petróleo" },
        // Amarelos e laranjas
        { hex: "#FACC15", name: "Amarelo" },
        { hex: "#EAB308", name: "Ouro" },
        { hex: "#F59E0B", name: "Âmbar" },
        { hex: "#FB923C", name: "Laranja claro" },
        { hex: "#F97316", name: "Laranja" },
        { hex: "#EA580C", name: "Laranja escuro" },
        // Vermelhos e rosas
        { hex: "#FF6B4A", name: "Coral" },
        { hex: "#F87171", name: "Vermelho claro" },
        { hex: "#EF4444", name: "Vermelho" },
        { hex: "#EC4899", name: "Rosa" },
        { hex: "#DB2777", name: "Pink" },
        { hex: "#BE123C", name: "Vinho" },
        // Roxos
        { hex: "#C084FC", name: "Lilás" },
        { hex: "#A855F7", name: "Roxo claro" },
        { hex: "#9333EA", name: "Roxo" },
        { hex: "#7C3AED", name: "Violeta" },
        { hex: "#6D28D9", name: "Roxo escuro" },
        { hex: "#4F46E5", name: "Índigo" },
        // Azuis
        { hex: "#60A5FA", name: "Azul claro" },
        { hex: "#3B82F6", name: "Azul" },
        { hex: "#2563EB", name: "Azul forte" },
        { hex: "#1D4ED8", name: "Azul escuro" },
        { hex: "#38BDF8", name: "Ciano" },
        { hex: "#0E7490", name: "Azul petróleo" },
        // Neutros e terrosos
        { hex: "#CBD5E1", name: "Cinza claro" },
        { hex: "#94A3B8", name: "Cinza" },
        { hex: "#64748B", name: "Cinza médio" },
        { hex: "#475569", name: "Grafite" },
        { hex: "#8B5E4A", name: "Marrom" },
        { hex: "#BFA98A", name: "Bege" },
    ];

    function hexToRgb(hex) {
        var normalized = (hex || "").replace("#", "");
        return {
            r: parseInt(normalized.substring(0, 2), 16),
            g: parseInt(normalized.substring(2, 4), 16),
            b: parseInt(normalized.substring(4, 6), 16),
        };
    }

    function relativeLuminance(hex) {
        var rgb = hexToRgb(hex);
        var channels = [rgb.r, rgb.g, rgb.b].map(function (value) {
            var c = value / 255;
            return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    }

    function contrastRatio(luminanceA, luminanceB) {
        var lighter = Math.max(luminanceA, luminanceB);
        var darker = Math.min(luminanceA, luminanceB);
        return (lighter + 0.05) / (darker + 0.05);
    }

    // Luminância relativa WCAG: nunca deixa o texto ilegível sobre a cor
    // escolhida. Espelha get_contrast_text() em core/colors.py.
    function getContrastText(backgroundHex) {
        var bgLuminance = relativeLuminance(backgroundHex);
        var contrastWithWhite = contrastRatio(bgLuminance, 1.0);
        var contrastWithBlack = contrastRatio(bgLuminance, 0.0);
        return contrastWithBlack > contrastWithWhite ? "#1F2937" : "#FFFFFF";
    }

    window.LPSColors = { PALETTE: PALETTE, getContrastText: getContrastText };
})();

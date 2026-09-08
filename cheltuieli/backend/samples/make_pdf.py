"""Build a minimal text PDF for local import tests."""

from pathlib import Path


def write_pdf(path: Path, lines: list[str]) -> None:
    content_lines = ["BT /F1 12 Tf 50 720 Td"]
    for i, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if i == 0:
            content_lines.append(f"({escaped}) Tj")
        else:
            content_lines.append(f"0 -18 Td ({escaped}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    write_pdf(
        root / "factura.pdf",
        [
            "FACTURA nr. F-2026-0042",
            "Furnizor: SC Exemplu Hosting SRL",
            "CUI RO12345678",
            "Data: 04.09.2026",
            "Descriere: Servicii gazduire web",
            "TOTAL DE PLATA 1.250,00",
            "TVA 226,89",
        ],
    )
    write_pdf(
        root / "extras.pdf",
        [
            "EXTRAS DE CONT 01.09.2026 - 04.09.2026",
            "IBAN RO49AAAA1B31007593840000",
            "02.09.2026 Mega Image Titan debit 125,90 RON",
            "03.09.2026 Petrom Calea Mosilor debit 280,00 RON",
            "03.09.2026 Digi Romania debit 69,00 RON",
            "Sold final 1.000,00",
        ],
    )
    print("samples written")

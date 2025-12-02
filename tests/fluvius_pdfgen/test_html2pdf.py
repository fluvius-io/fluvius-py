from fii_pdfgen import PdfAction, PdfPipeline, SignField, genpdf


def setup_html2pdf_template(template_id):
    w9op = PdfAction(
        "html2pdf",
        template="contract-management/TCH.Onboarding_Contract.01.w9_form.html",
        sign_fields=SignField(page=1),
    )

    return PdfPipeline([w9op], template_id=template_id)


def test_html2pdf():
    setup_html2pdf_template("html2pdf_test")
    result = genpdf(
        "html2pdf_test", {"ppa__w9_form": {"name": "Onboarding_Contract, LLC."}}
    )

    assert result.sign_fields[0].page == 1
    print(result)

from fii_pdfgen import PdfAction, PdfPipeline, genpdf


def test_noop():
    pipe = PdfPipeline([PdfAction("noop", test=123)])

    result = pipe.render({"ABC": "123"})

    print(repr(pipe))
    assert result == ({"ABC": "123"}, {"test": 123})


def test_concurrent():
    ops = (PdfAction("noop", test=123), PdfAction("noop", test=456))
    pipe = PdfPipeline([PdfAction("concurrent", actions=ops)])
    print(repr(pipe))

    result = pipe.render({"ABC": "123"})

    assert result == ({"ABC": "123"}, {"test": 123}, {"ABC": "123"}, {"test": 456})


def test_concatenate():
    ops = (PdfAction("noop", test=123), PdfAction("noop", test=456))
    pipe = PdfPipeline(
        [
            PdfAction("concurrent", actions=ops),
            PdfAction(
                "naive-concatenate",
                fixtures=[(-1, "header"), (0.5, "TOC"), (1000, "footer")],
            ),
        ]
    )

    (result,) = pipe.render({"ABC": "123"})

    assert result == (
        "header",
        {"ABC": "123"},
        "TOC",
        {"test": 123},
        {"ABC": "123"},
        {"test": 456},
        "footer",
    )


def test_template_id():
    def setup_template(_id):
        ops = (PdfAction("noop", test=123), PdfAction("noop", test=456))
        return PdfPipeline(
            [
                PdfAction("concurrent", actions=ops),
                PdfAction(
                    "naive-concatenate",
                    fixtures=[(-1, "header"), (0.5, "TOC"), (1000, "footer")],
                ),
            ],
            template_id=_id,
        )

    setup_template("test_template_id")
    result = genpdf("test_template_id", {"ABC": "123"})
    print(result)
    assert result == (
        "header",
        {"ABC": "123"},
        "TOC",
        {"test": 123},
        {"ABC": "123"},
        {"test": 456},
        "footer",
    )

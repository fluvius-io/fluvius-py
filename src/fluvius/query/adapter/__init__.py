    def parse_query(url_params, request_headers, request_params):
        '''
            query_prefix: Query identifier
            query_params: Query parameters
            headers: Request headers
            kwargs: Keyword arguments that is passed to the query
        '''
        def _parse_sort(args):
            sort = kwargs.get(SORT)
            if not sort:
                return

            try:
                sort = json.loads(sort)
            except ValueError:
                sort = filter(None, RX_SELECT_SPLIT.split(sort))

            def _gen():
                for statement in sort:
                    k, _, d = statement.partition(".")

                    try:
                        di = int(d)
                        d = "desc" if di < 0 else "asc"
                    except ValueError:
                        d = d or "asc"

                    yield (k, d)

            _sort = list(_gen())
            return _sort if _sort else None

        def _parse_select(select):
            if ALLOW_ESCAPE and select == SELECT_ESCAPE_CHAR:
                return select

            if not select:
                return None

            return [fn for fn in RX_SELECT_SPLIT.split(select) if fn]

        def _parse_pagination(args):
            limit = max(1, int(args.get(LIMIT, LIMIT_DEFAULT)))
            if PAGE in args:
                page = int(args.get(PAGE))
                offset = max(0, (page - 1) * limit)
                return limit, offset, page

            offset = 0
            if OFFSET in args:
                offset = max(0, int(args.get(OFFSET)))

            return limit, offset, int(offset / limit) + 1

        def _parse_where(args):
            qstr = args.get(QUERY)
            return json.loads(qstr) if qstr else None

        def _parse_text(args):
            text = args.get(TEXT)
            method = 'fts'

            if text is None:
                text = args.get(f'{TEXT}:kw')
                method = 'kw'

            if text is None:
                text = args.get(f'{TEXT}:fts')
                method = 'fts'

            return (text, method) if text else (None, None)

        def _parse_deleted(args):
            if (SHOW_DELETED not in args) or (not args[SHOW_DELETED]):
                return 0

            return min(2, max(0, int(args[SHOW_DELETED][0])))

        where = _parse_where(kwargs)
        sort = _parse_sort(kwargs)
        text, text_method = _parse_text(kwargs)
        limit, offset, page = _parse_pagination(kwargs)
        show_deleted = _parse_deleted(kwargs)

        return ParsedParams.create(
            {
                "sort": sort,
                "match": where,
                "offset": offset,
                "page": page,
                "limit": limit,
                "text": text,
                "select": _parse_select(args.get(SELECT)),
                "deselect": _parse_select(args.get(DESELECT)),
            }
        )

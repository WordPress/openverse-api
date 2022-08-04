[1mdiff --cc .github/workflows/ci_cd.yml[m
[1mindex 4c936852,1f70810a..00000000[m
[1m--- a/.github/workflows/ci_cd.yml[m
[1m+++ b/.github/workflows/ci_cd.yml[m
[36m@@@ -16,14 -15,7 +16,8 @@@[m [mjobs[m
      runs-on: ubuntu-latest[m
      steps:[m
        - name: Checkout repository[m
[31m -        uses: actions/checkout@v2[m
[32m +        uses: actions/checkout@v3[m
[32m +[m
[31m-       - name: Rebase[m
[31m-         if: github.event.input.rebase[m
[31m-         run: |[m
[31m-           git fetch main[m
[31m-           git rebase main[m
[31m- [m
        - name: Setup Python[m
          uses: actions/setup-python@v2[m
          with:[m
[36m@@@ -169,31 -162,28 +163,6 @@@[m
            name: api_logs[m
            path: api_logs[m
  [m
[31m-   test-redoc:[m
[31m-     name: Check for API consumer docs[m
[31m-     runs-on: ubuntu-latest[m
[31m -  validate-openapi-spec:[m
[31m -    name: Validate Open API spec[m
[31m -    runs-on: ubuntu-latest:[m
[31m--    needs:[m
[31m--      - build-images[m
[31m--    steps:[m
[31m-       - name: Checkout repository[m
[31m-         uses: actions/checkout@v2[m
[31m- [m
[31m-       - name: Setup just[m
[31m-         uses: extractions/setup-just@v1[m
[31m -      - uses: actions/checkout@v2[m
[31m -      - uses: extractions/setup-just@v1[m
[31m--[m
[31m--      - name: Download all images[m
[31m--        uses: actions/download-artifact@v2[m
[31m--        with:[m
[31m--          path: /tmp[m
[31m--[m
[31m--      - name: Load all images[m
[31m--        run: |[m
[31m--          docker load --input /tmp/api/api.tar[m
[31m--          docker load --input /tmp/ingestion_server/ingestion_server.tar[m
[31m--[m
[31m-       - name: Test ReDoc site[m
[31m-         run: just api-doctest[m
[31m -      - name: Run check[m
[31m -        run: just dj validateopenapischema[m
[31m--[m
    django-check:[m
      name: Run Django check[m
      runs-on: ubuntu-latest[m

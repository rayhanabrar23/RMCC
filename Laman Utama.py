# 4. Tampilkan Widget Login
    # PERBAIKAN FINAL: Form Name sebagai Argumen Posisi, sisanya Keyword
    name, authentication_status, username = authenticator.login(
        'Login Dashboard',         # <--- HANYA STRING NAMA FORM DI SINI
        location='main',           # <--- KEYWORD UNTUK LOKASI
        key='unique_login_key'     # <--- KEYWORD UNTUK KEY
    )

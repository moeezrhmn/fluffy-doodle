import browser_cookie3

def export_cookies():
    cookies = browser_cookie3.chrome(cookie_file="/tmp/chrome-profile/Default/Cookies")

    netscape_format = []
    for cookie in cookies:
        secure = "TRUE" if cookie.secure else "FALSE"
        netscape_format.append(f"{cookie.domain}\tTRUE\t{cookie.path}\t{secure}\t{cookie.expires}\t{cookie.name}\t{cookie.value}")

    with open("/tmp/cookies.txt", "w") as f:
        f.write("\n".join(netscape_format))

export_cookies()
print("Cookies exported to /tmp/cookies.txt")

// Send a plain-text email over SMTPS with libcurl.
//
// Usage:
//   export SMTP_PASSWORD=<QQ mail authorization code>
//   send_email <from@qq.com> <to1[,to2,...]> <subject> <body>
//
// Optional env:
//   SMTP_URL      (default: smtps://smtp.qq.com:465)
//   SMTP_VERBOSE  (set to anything to print the SMTP conversation)

#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <print>
#include <sstream>
#include <string>
#include <vector>
#include <curl/curl.h>

static std::vector<std::string> split(const std::string &s, char sep)
{
    std::vector<std::string> out;
    std::stringstream ss(s);
    for(std::string item; std::getline(ss, item, sep);){
        if(!item.empty()){
            out.push_back(item);
        }
    }
    return out;
}

// RFC 2047 encoding so non-ASCII (e.g. Chinese) subjects display correctly
static std::string encodeHeaderUTF8(const std::string &s)
{
    static constexpr char tbl[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string b64;
    for(size_t i = 0; i < s.size(); i += 3){
        uint32_t n = static_cast<uint32_t>(static_cast<uint8_t>(s[i])) << 16;
        if(i + 1 < s.size()) n |= static_cast<uint32_t>(static_cast<uint8_t>(s[i + 1])) << 8;
        if(i + 2 < s.size()) n |= static_cast<uint32_t>(static_cast<uint8_t>(s[i + 2]));

        b64 += tbl[(n >> 18) & 63];
        b64 += tbl[(n >> 12) & 63];
        b64 += (i + 1 < s.size()) ? tbl[(n >> 6) & 63] : '=';
        b64 += (i + 2 < s.size()) ? tbl[n & 63] : '=';
    }
    return "=?UTF-8?B?" + b64 + "?=";
}

int main(int argc, char *argv[])
{
    if(argc != 5){
        std::println(stderr, "usage: {} <from> <to1[,to2,...]> <subject> <body>", argv[0]);
        std::println(stderr, "env  : SMTP_PASSWORD (required), SMTP_URL (default smtps://smtp.qq.com:465), SMTP_VERBOSE");
        return 1;
    }

    const std::string from    = argv[1];
    const std::string toArg   = argv[2];
    const std::string subject = argv[3];
    const std::string body    = argv[4];
    const auto        toList  = split(toArg, ',');

    const char *password = std::getenv("SMTP_PASSWORD");
    const char *url      = std::getenv("SMTP_URL");

    if(!password || !*password){
        std::println(stderr, "SMTP_PASSWORD is not set");
        return 1;
    }

    if(toList.empty()){
        std::println(stderr, "no recipient given");
        return 1;
    }

    curl_global_init(CURL_GLOBAL_DEFAULT);
    CURL *curl = curl_easy_init();
    if(!curl){
        std::println(stderr, "curl_easy_init() failed");
        return 1;
    }

    const std::string mailFrom = "<" + from + ">";
    curl_easy_setopt(curl, CURLOPT_URL, (url && *url) ? url : "smtps://smtp.qq.com:465");
    curl_easy_setopt(curl, CURLOPT_USERNAME, from.c_str());
    curl_easy_setopt(curl, CURLOPT_PASSWORD, password);
    curl_easy_setopt(curl, CURLOPT_USE_SSL, static_cast<long>(CURLUSESSL_ALL));
    curl_easy_setopt(curl, CURLOPT_MAIL_FROM, mailFrom.c_str());

    curl_slist *rcpt = nullptr;
    for(const auto &to: toList){
        rcpt = curl_slist_append(rcpt, ("<" + to + ">").c_str());
    }
    curl_easy_setopt(curl, CURLOPT_MAIL_RCPT, rcpt);

    char dateBuf[64];
    const std::time_t now = std::time(nullptr);
    std::strftime(dateBuf, sizeof(dateBuf), "%a, %d %b %Y %H:%M:%S %z", std::localtime(&now));

    curl_slist *headers = nullptr;
    headers = curl_slist_append(headers, (std::string("Date: ") + dateBuf).c_str());
    headers = curl_slist_append(headers, ("From: " + mailFrom).c_str());
    headers = curl_slist_append(headers, ("To: " + toArg).c_str());
    headers = curl_slist_append(headers, ("Subject: " + encodeHeaderUTF8(subject)).c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

    curl_mime *mime = curl_mime_init(curl);
    curl_mimepart *part = curl_mime_addpart(mime);
    curl_mime_data(part, body.c_str(), CURL_ZERO_TERMINATED);
    curl_mime_type(part, "text/plain; charset=UTF-8");
    curl_mime_encoder(part, "base64");
    curl_easy_setopt(curl, CURLOPT_MIMEPOST, mime);

    if(std::getenv("SMTP_VERBOSE")){
        curl_easy_setopt(curl, CURLOPT_VERBOSE, 1L);
    }

    const CURLcode res = curl_easy_perform(curl);
    if(res == CURLE_OK){
        std::println("email sent to {}", toArg);
    }
    else{
        std::println(stderr, "curl_easy_perform() failed: {}", curl_easy_strerror(res));
    }

    curl_mime_free(mime);
    curl_slist_free_all(headers);
    curl_slist_free_all(rcpt);
    curl_easy_cleanup(curl);
    curl_global_cleanup();

    return res == CURLE_OK ? 0 : 1;
}

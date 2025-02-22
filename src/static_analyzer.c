#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zip.h>

// API 카테고리별 목록 정의
typedef struct {
    const char *name;
    const char *category;
} APIEntry;

// 분석할 API 목록 (JavaScript에서 직접 호출되는 함수 기반)
APIEntry target_apis[] = {
    // **File System API**
    {"document.querySelector('input[type=\"file\"]')", "File System"},
    {"file.name", "File System"},
    {"file.type", "File System"},
    {"file.size", "File System"},
    {"file.lastModified", "File System"},
    {"new Blob", "File System"},
    {"FileReader.readAsText", "File System"},
    {"FileReader.readAsDataURL", "File System"},
    {"FileReader.readAsArrayBuffer", "File System"},
    {"window.requestFileSystem", "File System"},
    {"fileEntry.createWriter", "File System"},
    {"indexedDB.open", "File System"},
    {"indexedDB.transaction", "File System"},
    {"store.put", "File System"},
    {"localStorage.setItem", "File System"},
    {"localStorage.getItem", "File System"},
    {"sessionStorage.setItem", "File System"},
    {"sessionStorage.getItem", "File System"},
    {"document.cookie", "File System"},
    {"navigator.clipboard.readText", "File System"},
    {"navigator.clipboard.writeText", "File System"},

    // **Network API**
    {"fetch", "Network"},
    {"new XMLHttpRequest", "Network"},
    {"new WebSocket", "Network"},
    {"navigator.sendBeacon", "Network"},
    {"new RTCPeerConnection", "Network"},
    {"chrome.webRequest.onBeforeRequest.addListener", "Network"},
    {"chrome.webRequest.onHeadersReceived.addListener", "Network"},
    {"chrome.identity.getAuthToken", "Network"},
    {"chrome.proxy.settings.set", "Network"},
    {"chrome.dns.resolve", "Network"},

    // **Rendering API**
    {"document.createElement", "Rendering"},
    {"document.appendChild", "Rendering"},
    {"element.innerHTML", "Rendering"},
    {"document.querySelector", "Rendering"},
    {"document.getElementById", "Rendering"},
    {"element.style", "Rendering"},
    {"new MutationObserver", "Rendering"},
    {"chrome.tabs.executeScript", "Rendering"},
    {"setTimeout", "Rendering"},
    {"setInterval", "Rendering"},
    {"canvas.getContext", "Rendering"},
    {"CanvasRenderingContext2D.drawImage", "Rendering"},
    {"document.designMode", "Rendering"},
    {"shadowRoot.attachShadow", "Rendering"},
    {"window.open", "Rendering"},
    {"chrome.windows.create", "Rendering"},
    {"chrome.tabs.create", "Rendering"},
    {"chrome.notifications.create", "Rendering"},

    // **User Interaction API**
    {"addEventListener", "User Interaction"},
    {"document.onmousemove", "User Interaction"},
    {"document.onkeypress", "User Interaction"},
    {"document.onkeydown", "User Interaction"},
    {"window.onbeforeunload", "User Interaction"},
    {"chrome.contextMenus.create", "User Interaction"},
    {"chrome.alarms.create", "User Interaction"},
    {"chrome.notifications.onClicked.addListener", "User Interaction"},
    {"chrome.permissions.request", "User Interaction"},
    {"chrome.tabs.onActivated.addListener", "User Interaction"},
    {"window.alert", "User Interaction"},
    {"window.confirm", "User Interaction"},
    {"window.prompt", "User Interaction"}
};

// API 개수
#define API_COUNT (sizeof(target_apis) / sizeof(target_apis[0]))

// 구조체 정의 (API 카운팅용)
typedef struct APINode {
    char *name;
    int count;
    struct APINode *next;
} APINode;

// 해시 테이블 크기
#define HASH_TABLE_SIZE 1024
APINode *api_table[HASH_TABLE_SIZE] = {0};

// 해시 함수
unsigned int hash_function(const char *str) {
    unsigned int hash = 0;
    while (*str) {
        hash = (hash * 31) + *str++;
    }
    return hash % HASH_TABLE_SIZE;
}

// API 카운트 증가
void add_api_count(const char *name) {
    unsigned int index = hash_function(name);
    APINode *node = api_table[index];

    while (node) {
        if (strcmp(node->name, name) == 0) {
            node->count++;
            return;
        }
        node = node->next;
    }

    node = (APINode *)malloc(sizeof(APINode));
    node->name = strdup(name);
    node->count = 1;
    node->next = api_table[index];
    api_table[index] = node;
}

// API 검출
void extract_apis(const char *content) {
    for (int i = 0; i < API_COUNT; i++) {
        const char *api = target_apis[i].name;
        const char *ptr = content;

        while ((ptr = strstr(ptr, api)) != NULL) {
            add_api_count(api);
            ptr += strlen(api);
        }
    }
}

// manifest.json에서 permissions 추출
void extract_permissions(const char *content) {
    const char *start = strstr(content, "\"permissions\"");
    if (!start) return;

    start = strchr(start, '[');
    if (!start) return;

    const char *end = strchr(start, ']');
    if (!end) return;

    printf("\n=== Permissions in manifest.json ===\n");
    fwrite(start, 1, end - start + 1, stdout);
    printf("\n");
}

// ZIP 파일 내 파일 검사
void analyze_zip(const char *zip_path) {
    struct zip *z = zip_open(zip_path, 0, NULL);
    if (!z) {
        fprintf(stderr, "Failed to open zip file: %s\n", zip_path);
        return;
    }

    int file_count = zip_get_num_entries(z, 0);
    for (int i = 0; i < file_count; i++) {
        const char *name = zip_get_name(z, i, 0);
        if (!name || strstr(name, "__MACOSX/") == name || strstr(name, "._") == name) continue;
        if (!strstr(name, ".js") && !strstr(name, ".json") && !strstr(name, "manifest.json")) continue;

        struct zip_stat st;
        zip_stat_init(&st);
        if (zip_stat(z, name, 0, &st) == 0) {
            char *content = malloc(st.size + 1);
            struct zip_file *zf = zip_fopen(z, name, 0);
            if (zf && content) {
                zip_fread(zf, content, st.size);
                content[st.size] = '\0';

                if (strstr(name, "manifest.json")) {
                    extract_permissions(content);
                } else {
                    extract_apis(content);
                }
				printf("Analyzing file: %s\n", name);

                free(content);
                zip_fclose(zf);
            }
        }
    }

    zip_close(z);
}
// API 분석 결과 출력 (카테고리별)
void print_api_results() {
    printf("\n=== API Usage Summary ===\n");

    const char *current_category = NULL;
    for (int i = 0; i < API_COUNT; i++) {
        unsigned int index = hash_function(target_apis[i].name);
        APINode *node = api_table[index];

        while (node) {
            if (strcmp(node->name, target_apis[i].name) == 0 && node->count > 0) {
                if (!current_category || strcmp(current_category, target_apis[i].category) != 0) {
                    printf("\n[%s]\n", target_apis[i].category);
                    current_category = target_apis[i].category;
                }
                printf("%s: %d\n", node->name, node->count);
            }
            node = node->next;
        }
    }
}
// 실행 진입점
int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <zip_file>\n", argv[0]);
        return 1;
    }
    analyze_zip(argv[1]);
	print_api_results();

    return 0;
}
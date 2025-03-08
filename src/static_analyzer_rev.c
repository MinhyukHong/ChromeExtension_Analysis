#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <dirent.h>
#include <string.h>
#include <zip.h>

#define SAMPLE_SIZE 500
#define MAX_PATH_LEN 512
#define OUTPUT_CSV "extension_analysis.csv"

// API 카테고리별 목록 정의
typedef struct {
    const char *name;
    const char *category;
} APIEntry;

// API 통계 저장 구조체
typedef struct APINode {
    char *name;
    int count;
    struct APINode *next;
} APINode;

// API 목록
APIEntry target_apis[] = {
    {"fetch", "Network"}, {"new XMLHttpRequest", "Network"},
    {"new WebSocket", "Network"}, {"navigator.sendBeacon", "Network"},
    {"new RTCPeerConnection", "Network"}, {"chrome.webRequest.onBeforeRequest.addListener", "Network"},
    {"chrome.webRequest.onHeadersReceived.addListener", "Network"},
    {"document.createElement", "Rendering"}, {"document.appendChild", "Rendering"},
    {"document.querySelector", "Rendering"}, {"document.getElementById", "Rendering"},
    {"element.innerHTML", "Rendering"}, {"setTimeout", "Rendering"},
    {"setInterval", "Rendering"}, {"chrome.tabs.executeScript", "Rendering"},
    {"chrome.windows.create", "Rendering"}, {"chrome.tabs.create", "Rendering"},
    {"chrome.notifications.create", "Rendering"}, {"window.open", "Rendering"},
    {"window.alert", "User Interaction"}, {"window.confirm", "User Interaction"},
    {"window.prompt", "User Interaction"}, {"chrome.permissions.request", "User Interaction"},
    {"chrome.tabs.onActivated.addListener", "User Interaction"}
};

#define API_COUNT (sizeof(target_apis) / sizeof(target_apis[0]))
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

// ZIP 내부 API 검출
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

// ZIP 파일 내 파일 검사
void analyze_zip(const char *zip_path) {
    struct zip *z = zip_open(zip_path, 0, NULL);
    if (!z) {
        fprintf(stderr, "[ERROR] Failed to open zip file: %s\n", zip_path);
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

                extract_apis(content);

                free(content);
                zip_fclose(zf);
            }
        }
    }

    zip_close(z);
}

// API 분석 결과 CSV 저장
void save_results_to_csv() {
    FILE *fp = fopen(OUTPUT_CSV, "w");
    if (!fp) {
        fprintf(stderr, "[ERROR] Cannot open CSV file for writing.\n");
        return;
    }

    fprintf(fp, "API,Count\n");
    for (int i = 0; i < API_COUNT; i++) {
        unsigned int index = hash_function(target_apis[i].name);
        APINode *node = api_table[index];

        while (node) {
            if (strcmp(node->name, target_apis[i].name) == 0 && node->count > 0) {
                fprintf(fp, "\"%s\",%d\n", node->name, node->count);
            }
            node = node->next;
        }
    }

    fclose(fp);
}

// Extension ZIP 파일 리스트를 가져옴
int get_extension_list(char extensions[][MAX_PATH_LEN], const char *folder_path) {
    struct dirent *entry;
    DIR *dir = opendir(folder_path);
    if (!dir) {
        fprintf(stderr, "[ERROR] Cannot open folder: %s\n", folder_path);
        return 0;
    }

    int count = 0;
    while ((entry = readdir(dir)) != NULL) {
        if (strstr(entry->d_name, ".zip")) {
            snprintf(extensions[count], MAX_PATH_LEN, "%s/%s", folder_path, entry->d_name);
            count++;
            if (count >= 5000) break;
        }
    }
    closedir(dir);
    return count;
}

// Extension 500개 랜덤 샘플링 후 분석
void sampling_analyze(const char *folder_path) {
    char extensions[5000][MAX_PATH_LEN];
    int total_extensions = get_extension_list(extensions, folder_path);
    if (total_extensions < SAMPLE_SIZE) {
        fprintf(stderr, "[ERROR] ZIP files are under 500 (%d found)\n", total_extensions);
        return;
    }

    srand(time(NULL));

    int sampled_indices[SAMPLE_SIZE] = {0};
    for (int i = 0; i < SAMPLE_SIZE; i++) {
        int idx;
        do {
            idx = rand() % total_extensions;
        } while (sampled_indices[idx]); // 중복 방지
        sampled_indices[idx] = 1;

        printf("[Analyzing] %s\n", extensions[idx]);
        analyze_zip(extensions[idx]);
    }

    save_results_to_csv();  // CSV 저장
}

// 실행 진입점
int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "[USAGE] %s <Folder containing ZIP files>\n", argv[0]);
        return 1;
    }

    sampling_analyze(argv[1]);

    return 0;
}

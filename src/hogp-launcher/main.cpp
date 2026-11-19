#include <windows.h>

#include <iostream>
#include <string>

int wmain(int argc, wchar_t** argv) {
    std::wstring command{L"mousse-hogp-packaged.exe"};
    for (int index = 1; index < argc; ++index) {
        command += L" \"";
        command += argv[index];
        command += L"\"";
    }
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE, 0, nullptr, nullptr,
                        &startup, &process)) {
        std::cerr << "Unable to activate packaged HOGP engine: " << GetLastError() << "\n";
        return 1;
    }
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exit_code{};
    GetExitCodeProcess(process.hProcess, &exit_code);
    CloseHandle(process.hProcess);
    return static_cast<int>(exit_code);
}

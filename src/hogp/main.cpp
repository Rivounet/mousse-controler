#include <windows.h>

#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <thread>
#include <utility>

#include <winrt/Windows.Devices.Bluetooth.GenericAttributeProfile.h>
#include <winrt/Windows.Devices.Bluetooth.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Storage.Streams.h>
#include <winrt/base.h>

using namespace winrt;
using namespace Windows::Devices::Bluetooth;
using namespace Windows::Devices::Bluetooth::GenericAttributeProfile;
using namespace Windows::Storage::Streams;

namespace {

constexpr std::array<std::uint8_t, 64> kMouseReportMap{
    0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x09, 0x01, 0xA1, 0x00,
    0x05, 0x09, 0x19, 0x01, 0x29, 0x05, 0x15, 0x00, 0x25, 0x01,
    0x95, 0x05, 0x75, 0x01, 0x81, 0x02, 0x95, 0x01, 0x75, 0x03,
    0x81, 0x03, 0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x16, 0x00,
    0x80, 0x26, 0xFF, 0x7F, 0x75, 0x10, 0x95, 0x02, 0x81, 0x06,
    0x09, 0x38, 0x15, 0x81, 0x25, 0x7F, 0x75, 0x08, 0x95, 0x01,
    0x81, 0x06, 0xC0, 0xC0};
static_assert(kMouseReportMap.size() == 64);

guid uuid(std::wstring_view value) { return guid{value}; }

IBuffer buffer(std::span<std::uint8_t const> bytes) {
    DataWriter writer;
    writer.WriteBytes(bytes);
    return writer.DetachBuffer();
}

template <std::size_t N>
IBuffer buffer(std::array<std::uint8_t, N> const& bytes) {
    return buffer(std::span<std::uint8_t const>{bytes});
}

std::string narrow(hstring const& value) { return to_string(value); }

bool advertisement_active(GattServiceProviderAdvertisementStatus status) {
    return status == GattServiceProviderAdvertisementStatus::Started ||
           status == GattServiceProviderAdvertisementStatus::StartedWithoutAllAdvertisementData;
}

template <typename T>
std::string enum_value(T value) {
    return std::to_string(static_cast<std::underlying_type_t<T>>(value));
}

std::string json_escape(std::string_view value) {
    std::ostringstream out;
    for (unsigned char ch : value) {
        switch (ch) {
        case '\\': out << "\\\\"; break;
        case '"': out << "\\\""; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (ch < 0x20) {
                out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                    << static_cast<int>(ch) << std::dec;
            } else {
                out << ch;
            }
        }
    }
    return out.str();
}

void emit(std::string_view event, bool ok, std::string_view detail = {}) {
    static std::mutex output_mutex;
    std::scoped_lock lock{output_mutex};
    std::cout << "{\"event\":\"" << json_escape(event) << "\",\"ok\":"
              << (ok ? "true" : "false");
    if (!detail.empty()) std::cout << ",\"detail\":\"" << json_escape(detail) << "\"";
    std::cout << "}" << std::endl;
}

GattLocalCharacteristicParameters static_parameters(
    GattCharacteristicProperties properties, IBuffer const& value) {
    GattLocalCharacteristicParameters parameters;
    parameters.CharacteristicProperties(properties);
    parameters.ReadProtectionLevel(GattProtectionLevel::EncryptionRequired);
    parameters.WriteProtectionLevel(GattProtectionLevel::EncryptionRequired);
    parameters.StaticValue(value);
    return parameters;
}

GattLocalCharacteristic create_characteristic(
    GattServiceProvider const& provider, wchar_t const* id,
    GattLocalCharacteristicParameters const& parameters, std::string_view name) {
    auto result = provider.Service().CreateCharacteristicAsync(uuid(id), parameters).get();
    if (result.Error() != BluetoothError::Success || !result.Characteristic()) {
        throw std::runtime_error(std::string{name} + ": " + enum_value(result.Error()));
    }
    return result.Characteristic();
}

class HogpEngine {
public:
    void prepare() {
        std::scoped_lock lock{mutex_};
        if (prepared_) return;
        auto adapter = BluetoothAdapter::GetDefaultAsync().get();
        if (!adapter || !adapter.IsPeripheralRoleSupported())
            throw std::runtime_error("Bluetooth peripheral role unavailable");

        auto hid_result = GattServiceProvider::CreateAsync(uuid(L"00001812-0000-1000-8000-00805f9b34fb")).get();
        if (hid_result.Error() != BluetoothError::Success || !hid_result.ServiceProvider())
            throw std::runtime_error("HID provider: " + enum_value(hid_result.Error()));
        hid_provider_ = hid_result.ServiceProvider();

        hid_information_ = create_characteristic(
            hid_provider_, L"00002a4a-0000-1000-8000-00805f9b34fb",
            static_parameters(GattCharacteristicProperties::Read,
                              buffer(std::array<std::uint8_t, 4>{0x11, 0x01, 0x00, 0x02})),
            "HID Information");
        report_map_ = create_characteristic(
            hid_provider_, L"00002a4b-0000-1000-8000-00805f9b34fb",
            static_parameters(GattCharacteristicProperties::Read, buffer(kMouseReportMap)),
            "Report Map");

        GattLocalCharacteristicParameters control_parameters;
        control_parameters.CharacteristicProperties(GattCharacteristicProperties::WriteWithoutResponse);
        control_parameters.ReadProtectionLevel(GattProtectionLevel::EncryptionRequired);
        control_parameters.WriteProtectionLevel(GattProtectionLevel::EncryptionRequired);
        control_point_ = create_characteristic(
            hid_provider_, L"00002a4c-0000-1000-8000-00805f9b34fb", control_parameters,
            "HID Control Point");

        GattLocalCharacteristicParameters report_parameters;
        report_parameters.CharacteristicProperties(
            GattCharacteristicProperties::Read | GattCharacteristicProperties::Notify);
        report_parameters.ReadProtectionLevel(GattProtectionLevel::EncryptionRequired);
        report_parameters.WriteProtectionLevel(GattProtectionLevel::EncryptionRequired);
        input_report_ = create_characteristic(
            hid_provider_, L"00002a4d-0000-1000-8000-00805f9b34fb", report_parameters,
            "Input Report");

        GattLocalDescriptorParameters descriptor_parameters;
        descriptor_parameters.ReadProtectionLevel(GattProtectionLevel::EncryptionRequired);
        descriptor_parameters.StaticValue(buffer(std::array<std::uint8_t, 2>{0x00, 0x01}));
        auto descriptor_result = input_report_.CreateDescriptorAsync(
            uuid(L"00002908-0000-1000-8000-00805f9b34fb"), descriptor_parameters).get();
        if (descriptor_result.Error() != BluetoothError::Success || !descriptor_result.Descriptor())
            throw std::runtime_error("Report Reference: " + enum_value(descriptor_result.Error()));

        auto battery_result = GattServiceProvider::CreateAsync(uuid(L"0000180f-0000-1000-8000-00805f9b34fb")).get();
        if (battery_result.Error() != BluetoothError::Success || !battery_result.ServiceProvider())
            throw std::runtime_error("Battery provider: " + enum_value(battery_result.Error()));
        battery_provider_ = battery_result.ServiceProvider();
        battery_level_ = create_characteristic(
            battery_provider_, L"00002a19-0000-1000-8000-00805f9b34fb",
            static_parameters(GattCharacteristicProperties::Read,
                              buffer(std::array<std::uint8_t, 1>{100})),
            "Battery Level");

        clients_token_ = input_report_.SubscribedClientsChanged(
            [this](GattLocalCharacteristic const& sender, Windows::Foundation::IInspectable const&) {
                std::scoped_lock event_lock{mutex_};
                subscribed_ = sender.SubscribedClients().Size() > 0;
                buttons_ = 0;
                emit("subscription", true, subscribed_ ? "subscribed" : "none");
                if (subscribed_) {
                    try { notify_locked(0, 0, 0, 0); }
                    catch (std::exception const& ex) { emit("release-on-subscribe", false, ex.what()); }
                }
            });
        advertisement_token_ = hid_provider_.AdvertisementStatusChanged(
            [this](GattServiceProvider const& sender,
               GattServiceProviderAdvertisementStatusChangedEventArgs const& args) {
                auto const status = sender.AdvertisementStatus();
                advertising_.store(advertisement_active(status));
                emit("advertisement",
                     args.Error() == BluetoothError::Success &&
                         status != GattServiceProviderAdvertisementStatus::Aborted,
                     "status=" + enum_value(status) + ",error=" + enum_value(args.Error()));
            });

        prepared_ = true;
        emit("prepared", true, "HID and Battery services created; advertising stopped");
    }

    void start_advertising() {
        std::scoped_lock lock{mutex_};
        ensure_prepared();
        if (advertisement_active(hid_provider_.AdvertisementStatus()))
            return;
        GattServiceProviderAdvertisingParameters parameters;
        parameters.IsConnectable(true);
        parameters.IsDiscoverable(true);
        hid_provider_.StartAdvertising(parameters);
        auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
        while (!advertisement_active(hid_provider_.AdvertisementStatus()) &&
               hid_provider_.AdvertisementStatus() != GattServiceProviderAdvertisementStatus::Aborted &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        auto const status = hid_provider_.AdvertisementStatus();
        advertising_.store(advertisement_active(status));
        if (!advertisement_active(status))
            throw std::runtime_error("advertising did not start; status=" + enum_value(status));
        emit("advertise-start", true);
    }

    void stop_advertising() noexcept { std::scoped_lock lock{mutex_}; stop_advertising_locked(); }

    void move(int dx, int dy) {
        if (dx < -32768 || dx > 32767 || dy < -32768 || dy > 32767)
            throw std::out_of_range("movement outside int16 bounds");
        std::scoped_lock lock{mutex_};
        notify_locked(buttons_, static_cast<std::int16_t>(dx), static_cast<std::int16_t>(dy), 0);
    }

    void scroll(int delta) {
        if (delta < -127 || delta > 127) throw std::out_of_range("wheel outside int8 bounds");
        std::scoped_lock lock{mutex_};
        notify_locked(buttons_, 0, 0, static_cast<std::int8_t>(delta));
    }

    void buttons(std::uint8_t value) {
        if ((value & 0xE0U) != 0) throw std::out_of_range("only buttons 1..5 are valid");
        std::scoped_lock lock{mutex_};
        notify_locked(value, 0, 0, 0);
        buttons_ = value;
    }

    void release_all() noexcept {
        std::scoped_lock lock{mutex_};
        if (!prepared_) return;
        try { if (subscribed_) notify_locked(0, 0, 0, 0); }
        catch (std::exception const& ex) { emit("release", false, ex.what()); }
        buttons_ = 0;
        emit("release", true);
    }

    void shutdown() noexcept {
        std::scoped_lock lock{mutex_};
        if (!prepared_) return;
        try { if (subscribed_) notify_locked(0, 0, 0, 0); } catch (...) {}
        buttons_ = 0;
        stop_advertising_locked();
        if (input_report_ && clients_token_) input_report_.SubscribedClientsChanged(std::exchange(clients_token_, {}));
        if (hid_provider_ && advertisement_token_) hid_provider_.AdvertisementStatusChanged(std::exchange(advertisement_token_, {}));
        input_report_ = nullptr;
        battery_provider_ = nullptr;
        hid_provider_ = nullptr;
        prepared_ = false;
        subscribed_ = false;
        emit("stopped", true);
    }

    void status() {
        std::scoped_lock lock{mutex_};
        std::ostringstream detail;
        detail << "prepared=" << prepared_ << ",advertising=" << advertising_.load()
               << ",advertisement_status="
               << (hid_provider_ ? enum_value(hid_provider_.AdvertisementStatus()) : "none")
               << ",subscribed=" << subscribed_ << ",buttons=" << static_cast<unsigned>(buttons_);
        emit("status", true, detail.str());
    }

private:
    void ensure_prepared() const { if (!prepared_) throw std::runtime_error("engine not prepared"); }

    void notify_locked(std::uint8_t buttons, std::int16_t dx, std::int16_t dy, std::int8_t wheel) {
        ensure_prepared();
        if (!subscribed_ || input_report_.SubscribedClients().Size() == 0) {
            subscribed_ = false;
            throw std::runtime_error("no subscribed HID host");
        }
        std::array<std::uint8_t, 6> report{
            buttons,
            static_cast<std::uint8_t>(dx & 0xFF),
            static_cast<std::uint8_t>((static_cast<std::uint16_t>(dx) >> 8) & 0xFF),
            static_cast<std::uint8_t>(dy & 0xFF),
            static_cast<std::uint8_t>((static_cast<std::uint16_t>(dy) >> 8) & 0xFF),
            static_cast<std::uint8_t>(wheel)};
        auto results = input_report_.NotifyValueAsync(buffer(report)).get();
        if (results.Size() == 0) throw std::runtime_error("notification reached no clients");
        for (auto const& result : results) {
            if (result.Status() != GattCommunicationStatus::Success)
                throw std::runtime_error("notification status: " + enum_value(result.Status()));
        }
        emit("report", true);
    }

    void stop_advertising_locked() noexcept {
        try {
            if (hid_provider_ && advertisement_active(hid_provider_.AdvertisementStatus()))
                hid_provider_.StopAdvertising();
        } catch (...) {}
        advertising_.store(false);
    }

    std::mutex mutex_;
    bool prepared_{false};
    std::atomic_bool advertising_{false};
    bool subscribed_{false};
    std::uint8_t buttons_{0};
    GattServiceProvider hid_provider_{nullptr};
    GattServiceProvider battery_provider_{nullptr};
    GattLocalCharacteristic hid_information_{nullptr};
    GattLocalCharacteristic report_map_{nullptr};
    GattLocalCharacteristic control_point_{nullptr};
    GattLocalCharacteristic input_report_{nullptr};
    GattLocalCharacteristic battery_level_{nullptr};
    event_token clients_token_{};
    event_token advertisement_token_{};
};

HogpEngine* g_engine{};

BOOL WINAPI console_handler(DWORD type) {
    if (type == CTRL_C_EVENT || type == CTRL_BREAK_EVENT || type == CTRL_CLOSE_EVENT || type == CTRL_SHUTDOWN_EVENT)
        if (g_engine) g_engine->shutdown();
    return FALSE;
}

int parse_int(std::istringstream& input, char const* name) {
    int value{};
    if (!(input >> value)) throw std::invalid_argument(std::string{"missing "} + name);
    return value;
}

} // namespace

int main(int argc, char** argv) {
    init_apartment(apartment_type::multi_threaded);
    HogpEngine engine;
    g_engine = &engine;
    SetConsoleCtrlHandler(console_handler, TRUE);
    if (argc != 2 || std::string_view{argv[1]} != "--stdio") {
        std::cerr << "Usage: mousse-hogp --stdio\n";
        return 2;
    }
    try {
        engine.prepare();
        std::string line;
        while (std::getline(std::cin, line)) {
            try {
                std::istringstream input{line};
                std::string command;
                input >> command;
                if (command.empty()) continue;
                if (command == "status") engine.status();
                else if (command == "advertise") {
                    std::string action; input >> action;
                    if (action == "start") engine.start_advertising();
                    else if (action == "stop") engine.stop_advertising();
                    else throw std::invalid_argument("advertise expects start or stop");
                } else if (command == "move") engine.move(parse_int(input, "dx"), parse_int(input, "dy"));
                else if (command == "scroll") engine.scroll(parse_int(input, "delta"));
                else if (command == "buttons") {
                    int value = parse_int(input, "mask");
                    if (value < 0 || value > 255) throw std::out_of_range("invalid mask");
                    engine.buttons(static_cast<std::uint8_t>(value));
                } else if (command == "release") engine.release_all();
                else if (command == "stop") { engine.shutdown(); break; }
                else throw std::invalid_argument("unknown command");
            } catch (std::exception const& ex) { emit("command", false, ex.what()); }
        }
    } catch (hresult_error const& ex) {
        emit("fatal", false, narrow(ex.message())); engine.shutdown(); return 1;
    } catch (std::exception const& ex) {
        emit("fatal", false, ex.what()); engine.shutdown(); return 1;
    }
    engine.shutdown();
    g_engine = nullptr;
    return 0;
}

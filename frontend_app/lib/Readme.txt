Snapbill - FRONTEND ARCHITECTURE DOCUMENTATION
SECTION 1 — Project Overview
1.1 Purpose
"My Kirana" is a mobile Point of Sale (POS) and inventory management application designed for small Indian retail shops (Kirana stores). It streamlines billing through multiple interfaces (Voice, Manual, Frequent) and manages inventory with support for localization (Hindi/English).

1.2 High-Level Architecture
The application follows a Clean Architecture principle, utilizing the Provider pattern for state management. It separates the Codebase into three distinct layers:

Presentation Layer (UI): Screens and Widgets.

Domain Layer (Providers/Models): Business logic and State.

Data Layer (Services/Core): API communication and static data.

1.3 Frontend-Backend Interaction
The Flutter frontend acts as a client interface. It does not perform heavy AI processing or database storage locally.

Protocol: REST API (HTTP).

Backend: FastAPI (Python).

Data Exchange: JSON.

AI: Audio/Text is sent to the backend; the backend processes it via Gemini and returns structured bill data.

SECTION 2 — Folder Tree
The project structure is organized by feature and responsibility:

lib/
├── main.dart                     # Application Entry Point
├── core/                         # Global Configurations
│   ├── theme.dart                # AppColors and Theme Data
│   └── master_list.dart          # Static/Fallback Inventory Data
├── models/                       # Data Structures
│   ├── item.dart                 # Inventory Item Model
│   └── shop_details.dart         # User/Shop Profile Model
├── providers/                    # State Management (Business Logic)
│   ├── auth_provider.dart        # User Authentication State
│   └── inventory_provider.dart   # Inventory CRUD & Filtering
├── services/                     # External Communication
│   ├── api_client.dart           # HTTP Wrapper & Interceptors
│   └── inventory_service.dart    # Inventory API endpoints
├── screens/                      # UI Pages
│   ├── splash_screen.dart        # Initial Loading
│   ├── auth_selection_screen.dart# Login/Signup Choice
│   ├── registration_screen.dart  # Sign Up UI
│   ├── login_screen.dart         # Sign In UI
│   ├── otp_screen.dart           # OTP Verification
│   ├── home_screen.dart          # Main Tab Controller
│   ├── voice_assistant_screen.dart # AI Billing UI
│   ├── inventory_screen.dart     # Stock Management UI
│   ├── frequent_billing_screen.dart # Quick Grid Billing UI
│   ├── history_screen.dart       # Past Bills UI
│   └── profile_screen.dart       # User Settings & Config
└── widgets/                      # Reusable UI Components
    └── bill_receipt_widget.dart  # Digital Bill Preview & Popup
SECTION 3 — Application Entry (main.dart)
This file initializes the environment before the UI loads.

3.1 main()
WidgetsFlutterBinding.ensureInitialized(): Essential for initializing native plugins (Bluetooth, Shared Preferences) before the app starts.

Orientation Locking: Calls SystemChrome.setPreferredOrientations to restrict the app to Portrait Up/Down. This prevents UI overflow errors common in landscape mode on small devices.

runApp(const MyKiranaApp()): Inflates the root widget.

3.2 MyKiranaApp Class
MultiProvider: Wraps the entire application. This injects AuthProvider and InventoryProvider at the root level, making state accessible to every screen without passing arguments down the tree.

MaterialApp:

theme: Applies the global theme from core/theme.dart.

home: Sets SplashScreen as the first view to handle logic (auto-login check).

SECTION 4 — Core Layer
4.1 core/theme.dart
Purpose: Centralizes design constants.

Key Properties:

AppColors: Defines primaryGreen, background, textBlack, etc.

ThemeData: configures default Card shapes (rounded corners), TextField styles (borders), and AppBar styling.

4.2 core/master_list.dart
Purpose: Contains a static list of ~100+ common Indian grocery items (e.g., Chawal, Dal, Masale).

Usage: Used by InventoryProvider to seed the app with data immediately, preventing an "empty state" experience before the backend syncs.

SECTION 5 — Service Layer
Services handle "dirty" work like network calls and data parsing.

5.1 services/api_client.dart
baseUrl: Points to the FastAPI backend (e.g., http://10.101.185.207:8000).

post(endpoint, data):

Retrieves the JWT token from SharedPreferences.

Injects Authorization: Bearer <token> header.

Encodes data to JSON.

Sends HTTP POST.

Throws exceptions on non-200 status codes.

get(endpoint): Similar to POST but for retrieving data.

5.2 services/inventory_service.dart
getItems(): Fetches shop-specific items from the backend.

addItem(Item item): Sends a new item payload to the backend.

deleteItem(String id): Sends a DELETE request for a specific Item ID.

SECTION 6 — Models
Models convert JSON to Dart Objects and vice-versa.

6.1 models/item.dart
Represents a single product.

Fields:

id (String): Unique identifier.

names (List<String>): Stores multiple aliases (e.g., ["Rice", "Chawal", "Tandul"]).

price (double): Cost per unit.

unit (String): Unit of measurement (kg, plate, packet).

category (String): Grouping key (Anaaj, Masale).

toJson(): Converts object to Map for API transmission.

fromJson(): Factory constructor to create object from API response.

6.2 models/shop_details.dart
Represents the user profile.

Fields: shopName, ownerName, address, phone1, phone2.

SECTION 7 — State Management
The app uses Provider (ChangeNotifier) to decouple logic from UI.

7.1 providers/inventory_provider.dart
State: List<Item> _items.

Initialization: Loads masterInventoryList on startup.

fetchItems(): Calls API to get backend data and merges it with the local master list.

getFilteredItems(query): Filters the list based on search text or selected category.

addItem(item): Updates the local list immediately (Optimistic UI) then calls the API.

deleteItem(id): Removes from local list immediately then calls API.

7.2 providers/auth_provider.dart
State: _token, _shopDetails.

verifyOtp(): Calls API to validate OTP. On success, saves Token and User Data to SharedPreferences and updates state.

tryAutoLogin(): Checks local storage for a valid token on app launch.

SECTION 8 — Screens
8.1 Authentication (login_screen.dart, otp_screen.dart)
Flow: User enters Phone -> AuthProvider.sendOtp() -> User enters OTP -> AuthProvider.verifyOtp().

Navigation: On success, Navigator.pushAndRemoveUntil to HomeScreen.

8.2 Home (home_screen.dart)
Purpose: Holds the BottomNavigationBar and manages the PageView.

Printer Initialization: Initializes Bluetooth Thermal Printer instance here to keep the connection alive across tabs.

8.3 Inventory (inventory_screen.dart)
UI: Search bar, Category Chips, List of Items.

Logic:

Edit/Add: Opens a Dialog with 4 Name fields (Hindi/English/Aliases) and a Unit selector.

Unit Selector: A smart widget that shows a Dropdown. If "Other" is selected, it renders a TextField for manual input.

Delete: Red button located inside the Edit Dialog to prevent accidental swipes.

8.4 Frequent Billing (frequent_billing_screen.dart)
UI: Grid of commonly used items (Samosa, Tea).

Logic: Tap to add to bill. Long press to Edit.

Safety: If "Print" is clicked, it checks isPrinterConnected. If false, shows a red Snackbar error and halts execution.

8.5 Voice Assistant (voice_assistant_screen.dart)
UI: Big microphone button, animated pulse.

Services: speech_to_text, flutter_tts (Text to Speech).

Flow:

User speaks ("1 kg sugar").

Text sent to Backend (Gemini).

Backend returns structured JSON (Item: Sugar, Qty: 1kg, Price: 40).

App adds to _currentBill.

Safety: Explicitly blocks saving/printing if Printer is disconnected.

8.6 History (history_screen.dart)
UI: List of cards showing Date, Time, and Total Amount.

Popup: Tapping a card opens a detailed BillReceiptWidget containing the full itemized table (not just the total).

8.7 Profile (profile_screen.dart)
UI: Shop details (Editable), Settings toggles.

Toggles:

Language: Hindi/English (Green highlight logic).

Template: Template 1/Template 2.

Preview: Shows a live rendering of a receipt with sample data (Rice, Sugar, Milk, Soap).

SECTION 9 — Widgets
9.1 BillReceiptWidget
Purpose: A highly reusable component that renders the bill receipt.

Capabilities:

Dynamic Language (Hindi/English headers).

Dynamic Data (Takes a list of items).

QR Code support (Optionally displays UPI QR).

Used in: ProfileScreen (Preview) and HistoryScreen (Detail View).

SECTION 10 — Inventory System Logic
The Inventory system is designed for flexibility regarding item naming.

Aliases: Each item supports names as a List<String>.

Index 0: Primary Name (e.g., Chawal).

Index 1: Secondary Name (e.g., Rice).

Index 2-3: Regional Aliases (e.g., Tandul).

Search: The getFilteredItems function in the provider searches all aliases. Typing "Rice" will find "Chawal".

Unit Handling: Users can select standard units (kg, plate) or type custom ones (glass, bundle). This is handled via a conditional UI render in the dialog.

SECTION 11 — Printer & Bluetooth
Plugin: blue_thermal_printer.

Discovery: The app scans for paired Bluetooth devices.

Commands: Uses esc_pos_utils_plus to generate raw byte commands (Text formatting, Tables, Cut Paper) for thermal printers.

Persistence: The connection state is managed in HomeScreen and passed down to child screens (Voice, Frequent) to ensure the printer stays connected while switching tabs.

SECTION 12 — Orientation
Constraint: The app is strictly locked to Portrait Mode.

Reason: The UI (lists, receipts, grids) is optimized for handheld vertical usage. Landscape mode breaks the layout.

Implementation: SystemChrome.setPreferredOrientations(...) inside main().

SECTION 13 — Authentication Flow (End-to-End)
Start: User opens app. SplashScreen checks SharedPreferences for user_token.

If No Token: User routed to AuthSelectionScreen.

Input: User enters Mobile Number.

Backend: auth_provider calls /auth/send-otp. Backend generates OTP (Mock '123456' for now).

Verify: User enters OTP. auth_provider calls /auth/verify-otp.

Response: Backend returns JWT Token + Shop Details.

Storage: App saves Token and Shop Details to SharedPreferences.

Session: User redirected to HomeScreen.

SECTION 14 — Backend Communication
Base URL: Configured in api_client.dart (Currently a local IP).

Authorization: Every API call (except Auth) injects the JWT token.

Data Models: The app expects specific JSON keys (names, price, unit). The fromJson factories in models/ map these strictly.

Error Handling: try-catch blocks in Providers catch network errors and display them via ScaffoldMessenger (Snackbars).

SECTION 15 — Data Flow Diagram (Text)
Scenario: User adds an item via Voice.

UI (VoiceScreen): User speaks "Add 1kg Rice".

Service (STT): Converts audio to text "Add 1kg Rice".

Service (API): Sends text to Backend (/ai/process).

Backend (FastAPI): Uses Gemini to parse text -> Returns JSON {"item": "Rice", "qty": "1kg", "price": 45}.

UI: Updates _currentBill list.

User Action: Clicks "Print".

UI Check: Checks isPrinterConnected.

Hardware: Sends Byte Data to Bluetooth Printer.

Provider: Adds Bill to History List.

SECTION 16 — Common Debug Points
Connection Refused (111/110):

Cause: Phone cannot reach Laptop/Backend.

Fix: Ensure both are on the Same Wi-Fi. Check Windows Firewall (Allow Port 8000). Verify IP in api_client.dart.

Printer Not Found:

Cause: Bluetooth permissions missing or Device not paired in Android Settings.

Fix: Pair device in Android Bluetooth settings before opening the app.

Missing Items:

Cause: Backend DB is empty.

Fix: The app uses master_list.dart as a fallback to ensure items always appear.

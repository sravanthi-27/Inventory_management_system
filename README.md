# Inventory Management System
## Overview

The Inventory Management System is a robust and user-friendly desktop application designed to streamline inventory operations for businesses of all sizes. Built with Python and PyQt5, it provides a comprehensive suite of tools for tracking items, managing categories, monitoring stock levels, and generating essential reports. The system utilizes a SQLite database for efficient and reliable data storage.

## Features

**Secure User Authentication:** Login system with an admin user (default credentials: admin/admin) for secure access.

_**Intuitive Dashboard:**_

**Real-time display of key metrics:** Total Items, Low Stock Items, and Total Categories.

Interactive bar chart visualizing top 10 item stock levels, with color-coded alerts for low stock.

**Comprehensive Item Management:**

Add, update, and delete inventory items with details like name, category, quantity, price, minimum stock, and supplier.
Dynamic table display with customizable sorting (currently by ID).
Low stock items are visually highlighted in the table for quick identification.
Search and filter capabilities by item name and category.

**Category Management:**

Organize items into categories.
Add, update, and delete categories with names and descriptions.
Automatic handling of item categorization upon category deletion (items become uncategorized).

**Reporting & Export:**

- **Generate on-demand reports:**

Low Stock Report, Full Inventory Report, and Category Report.

Export inventory data to Excel (.xlsx) for further analysis.

Export detailed inventory reports to PDF (.pdf) for professional documentation.

User-Friendly Interface: Built with PyQt5 for a clean, modern, and responsive graphical user interface.

SQLite Database: Lightweight, file-based database for easy setup and deployment.

## Technologies Used

- **Python 3.x:** The core programming language.

- **PyQt5:** For building the graphical user interface.

- **SQLite3:** For database management.

- **pandas:** For efficient data handling and Excel export.

- **openpyxl:** Python library required by pandas for .xlsx file operations.

- **matplotlib:** For plotting charts on the dashboard.

- **reportlab:** For generating PDF reports.

- **hashlib:** For secure password hashing.

## Installation & Setup

To run this application, follow these steps:

- Clone the repository (if applicable) or download the project files.

- Install Python 3.x:

If you don't have Python installed, download it from python.org.

- Install required Python packages:

Open your terminal or command prompt and run:

**pip install PyQt5 pandas openpyxl matplotlib reportlab**

Run the application:

Navigate to the project directory in your terminal and execute:

python your_main_script_name.py
(Replace your_main_script_name.py with the actual name of your Python file, e.g., inventory_app.py or similar.)

## Usage

**- Login:** Upon launching, you will be prompted to log in.

**- Default Admin Credentials:** username: admin, password: admin

**- Navigate Tabs**: Use the tabs (Dashboard, Items, Categories, Reports) to switch between different functionalities.

**- Toolbar Actions:** The toolbar provides quick access to refresh data, export options, and logout.

**- Data Interaction:**__

**- Items/Categories:** Use the forms to add new entries. Select an item/category from the table/list to populate the form for editing or deletion.

**- Reports:** Click the respective buttons in the Reports tab to generate and view reports.

**- Database Structure**

The application uses an inventory.db SQLite database with the following tables:

**- users:** Stores user authentication data (id, username, password, role).
**- categories:** Stores product categories (id, name, description).
**- items:** Stores inventory items (id, name, category_id, quantity, price, min_stock, supplier, date_added).
category_id has a FOREIGN KEY constraint that sets it to NULL if the referenced category is deleted, ensuring data integrity.
Contributing
(Optional section - remove if not applicable)
If you'd like to contribute to this project, please feel free to fork the repository, make your changes, and submit a pull request.

## License

This project is licensed under the MIT License.

## Screenshots

Here are some screenshots showcasing the application's interface and features:

## **login view** 

The application starts with a secure login screen to ensure only authorized users can access the inventory system.

![Screenshot 2025-05-26 205119](https://github.com/user-attachments/assets/aa302f2a-1146-4f68-b1eb-25cbe3f9a329)


## ** Dashboard View**

The main dashboard provides a quick overview of inventory statistics and stock levels.

![image](https://github.com/user-attachments/assets/37b255fb-4985-4a7a-87aa-a2aa4f086e2e)


## **Items Management**

Manage your inventory items with options to add, edit, delete, and filter.

![image](https://github.com/user-attachments/assets/3002d02c-72f6-416d-adc5-af7f9ac14684)


## **Category Management**

Organize your products into categories for better management.

![image](https://github.com/user-attachments/assets/528d1986-5563-449d-8dd1-ea7df03e9ab4)


## **Reports & Export**

Generate various reports and export data to Excel or PDF.
![image](https://github.com/user-attachments/assets/ba8c2ce2-a255-42ce-b5ee-d6eed4d26fcf)
![image](https://github.com/user-attachments/assets/daf91417-fd38-403b-8d28-5e91e9503ee6)
![image](https://github.com/user-attachments/assets/06d08995-f636-49d0-a405-15925d5c52b2)
![image](https://github.com/user-attachments/assets/6ce9cd8b-91a6-4225-961e-86b50d7c0f0d)





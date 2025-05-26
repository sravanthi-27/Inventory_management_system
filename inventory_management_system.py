#low item stocks appear in pink color
import sys
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QDialog, QMessageBox,
    QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QGroupBox, QListWidget,
    QListWidgetItem, QTextEdit, QAction, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont # QIcon removed as it was causing warnings without resource file
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Database Manager
class DatabaseManager:
    def __init__(self, db_name="inventory.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')

        # Categories table
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT)''')

        # Items table with ON DELETE SET NULL for category_id
        # This means if a category is deleted, items previously in that category will have category_id set to NULL.
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER, quantity INTEGER,
            price REAL, min_stock INTEGER, supplier TEXT, date_added TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL)''')

        # Add default admin user
        # Check if admin already exists to prevent integrity errors on subsequent runs
        cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', ?, 'admin')",
                       (hashlib.sha256('admin'.encode()).hexdigest(),))

        conn.commit()
        conn.close()

    def execute_query(self, query, params=(), fetch=False):
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row # Allows accessing columns by name
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall() if fetch else None
            conn.commit()
            return result
        except sqlite3.IntegrityError as e:
            # Catch specific integrity errors like UNIQUE constraint violations
            print(f"Database Integrity Error: {e}")
            raise # Re-raise the exception so it can be caught by the calling UI function
        except Exception as e:
            # Catch other general database errors
            print(f"Database error: {e}")
            raise # Re-raise other exceptions as well
        finally:
            if conn:
                conn.close()

# Modern Styled Widget Base
class StyledWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget { background-color: #f5f5f5; font-family: 'Segoe UI'; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                padding: 8px; border: 2px solid #ddd; border-radius: 5px;
                background-color: white; font-size: 14px; }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border-color: #4CAF50; }
            QPushButton {
                padding: 10px 20px; background-color: #4CAF50; color: white;
                border: none; border-radius: 5px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
            QTableWidget {
                gridline-color: #ddd; background-color: white;
                alternate-background-color: #f9f9f9; }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background-color: #4CAF50; color: white; }
            QHeaderView::section {
                background-color: #2196F3; color: white; padding: 10px;
                font-weight: bold; border: none; }
            QTabWidget::pane { border: 1px solid #ddd; background-color: white; }
            QTabBar::tab {
                background-color: #e0e0e0; padding: 10px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #4CAF50; color: white; }
            QGroupBox {
                font-weight: bold; border: 2px solid #ddd; border-radius: 5px;
                margin: 10px; padding-top: 10px; }
            QListWidget {
                border: 2px solid #ddd; border-radius: 5px; background-color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4CAF50; color: white;
            }
        """)

# Login Dialog
class LoginDialog(QDialog, StyledWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.user_role = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Inventory Management - Login")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        # Logo/Title
        title = QLabel("INVENTORY MANAGER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3; margin: 20px;")

        # Login form
        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)

        # Buttons
        btn_layout = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        btn_layout.addWidget(login_btn)

        layout.addWidget(title)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def login(self):
        username = self.username.text()
        password = hashlib.sha256(self.password.text().encode()).hexdigest()

        try:
            result = self.db_manager.execute_query(
                "SELECT role FROM users WHERE username=? AND password=?",
                (username, password), fetch=True)

            if result:
                self.user_role = result[0][0]
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Invalid credentials!")
        except Exception as e:
            QMessageBox.critical(self, "Login Error", f"An error occurred during login: {e}")


# Chart Widget
class ChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 6), facecolor='white')
        super().__init__(self.figure)
        self.setParent(parent)

    def plot_stock_levels(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if data:
            items, quantities = zip(*data)
            colors = ['red' if q <= 0 else 'orange' if q < 10 else 'green' for q in quantities] # Improved color logic
            ax.bar(range(len(items)), quantities, color=colors)
            ax.set_xticks(range(len(items)))
            ax.set_xticklabels(items, rotation=45, ha='right')
            ax.set_ylabel('Quantity')
            ax.set_title('Top 10 Item Stock Levels')
            ax.grid(axis='y', linestyle='--', alpha=0.7) # Add grid for better readability
        else:
            ax.text(0.5, 0.5, "No item data available for chart.",
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='gray')


        self.figure.tight_layout()
        self.draw()

# Main Application
class InventoryApp(QMainWindow, StyledWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.current_user_role = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Advanced Inventory Management System")
        self.setGeometry(100, 100, 1200, 800)

        # Login first
        login_dialog = LoginDialog(self.db_manager)
        if login_dialog.exec_() == QDialog.Accepted:
            self.current_user_role = login_dialog.user_role
        else:
            sys.exit()

        # Central widget with tabs
        central_widget = QTabWidget()
        self.setCentralWidget(central_widget)

        # Dashboard tab
        self.dashboard_widget = self.create_dashboard()
        central_widget.addTab(self.dashboard_widget, "Dashboard")

        # Items management tab
        self.items_widget = self.create_items_tab()
        central_widget.addTab(self.items_widget, "Items")

        # Categories tab
        self.categories_widget = self.create_categories_tab()
        central_widget.addTab(self.categories_widget, "Categories")

        # Reports tab
        self.reports_widget = self.create_reports_tab()
        central_widget.addTab(self.reports_widget, "Reports")

        # Toolbar
        self.create_toolbar()

        # Status bar
        self.statusBar().showMessage(f"Logged in as: {self.current_user_role.capitalize()}")

        # Load initial data
        self.load_categories() # Categories loaded first as items depend on them
        self.load_items()
        self.update_dashboard()

    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False) # Prevent toolbar from being moved

        # Refresh action - Icons removed to prevent warnings if not using .qrc
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_all_data)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # Export actions - Icons removed
        export_excel_action = QAction("Export Excel", self)
        export_excel_action.triggered.connect(self.export_to_excel)
        toolbar.addAction(export_excel_action)

        export_pdf_action = QAction("Export PDF", self)
        export_pdf_action.triggered.connect(self.export_to_pdf)
        toolbar.addAction(export_pdf_action)

        toolbar.addSeparator()

        # Logout action - Icons removed
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        toolbar.addAction(logout_action)

    def create_dashboard(self):
        """Create dashboard with analytics"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Stats cards
        stats_layout = QHBoxLayout()

        # Total items card
        total_items_count = self.db_manager.execute_query("SELECT COUNT(*) FROM items", fetch=True)[0][0]
        self.total_items_card = self.create_stat_card("Total Items", str(total_items_count), "#2196F3", "totalItemsLabel")
        stats_layout.addWidget(self.total_items_card)

        # Low stock items
        low_stock_count = self.db_manager.execute_query(
            "SELECT COUNT(*) FROM items WHERE quantity <= min_stock", fetch=True)[0][0]
        self.low_stock_card = self.create_stat_card("Low Stock", str(low_stock_count), "#f44336", "lowStockLabel")
        stats_layout.addWidget(self.low_stock_card)

        # Total categories
        total_categories_count = self.db_manager.execute_query("SELECT COUNT(*) FROM categories", fetch=True)[0][0]
        self.categories_card = self.create_stat_card("Categories", str(total_categories_count), "#4CAF50", "categoriesLabel")
        stats_layout.addWidget(self.categories_card)

        layout.addLayout(stats_layout)

        # Chart
        self.chart_widget = ChartWidget()
        layout.addWidget(self.chart_widget)

        widget.setLayout(layout)
        return widget

    def create_stat_card(self, title, value, color, object_name_suffix=""):
        """Create a statistics card"""
        card = QGroupBox()
        card.setFixedSize(250, 120) # Fixed size for consistency
        card.setStyleSheet(f"QGroupBox {{ border: 3px solid {color}; border-radius: 10px; }}")

        layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; color: #666; margin-bottom: 5px;")

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"font-size: 38px; font-weight: bold; color: {color};")
        value_label.setObjectName(f"statValueLabel_{object_name_suffix}") # Unique object name

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.setAlignment(Qt.AlignCenter) # Center content within the group box
        card.setLayout(layout)

        return card

    def create_items_tab(self):
        """Create items management tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Search and filter
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.filter_items)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentTextChanged.connect(self.filter_items)

        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addStretch() # Push category filter to the right
        search_layout.addWidget(QLabel("Category:"))
        search_layout.addWidget(self.category_filter)

        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels([
            "ID", "Name", "Category", "Quantity", "Price", "Min Stock", "Supplier", "Date Added"
        ])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SingleSelection) # Allow only single row selection
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Make table non-editable
        self.items_table.setAlternatingRowColors(True)
        self.items_table.itemClicked.connect(self.load_item_details_to_form) # Load details on click

        # Item form
        form_group = QGroupBox("Add/Edit Item")
        form_layout = QFormLayout()

        self.item_name = QLineEdit()
        self.item_category = QComboBox()
        self.item_quantity = QSpinBox()
        self.item_quantity.setRange(0, 999999)
        self.item_price = QDoubleSpinBox()
        self.item_price.setRange(0, 999999.99)
        self.item_price.setDecimals(2)
        self.item_min_stock = QSpinBox()
        self.item_min_stock.setRange(0, 999999)
        self.item_supplier = QLineEdit()

        form_layout.addRow("Name:", self.item_name)
        form_layout.addRow("Category:", self.item_category)
        form_layout.addRow("Quantity:", self.item_quantity)
        form_layout.addRow("Price:", self.item_price)
        form_layout.addRow("Min Stock:", self.item_min_stock)
        form_layout.addRow("Supplier:", self.item_supplier)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Item")
        add_btn.clicked.connect(self.add_item)
        update_btn = QPushButton("Update Item")
        update_btn.clicked.connect(self.update_item)
        delete_btn = QPushButton("Delete Item")
        delete_btn.clicked.connect(self.delete_item)
        delete_btn.setStyleSheet("QPushButton { background-color: #f44336; }")
        clear_btn = QPushButton("Clear Form") # New clear button
        clear_btn.clicked.connect(self.clear_item_form)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(clear_btn)

        form_layout.addRow(btn_layout)
        form_group.setLayout(form_layout)

        layout.addLayout(search_layout)
        layout.addWidget(self.items_table)
        layout.addWidget(form_group)

        widget.setLayout(layout)
        return widget

    def create_categories_tab(self):
        """Create categories management tab"""
        widget = QWidget()
        layout = QHBoxLayout()

        # Categories list
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(200)
        self.categories_list.itemClicked.connect(self.load_category_details)

        # Category form
        form_group = QGroupBox("Add/Edit Category")
        form_layout = QFormLayout()

        self.category_name = QLineEdit()
        self.category_description = QTextEdit()
        self.category_description.setMaximumHeight(100)

        form_layout.addRow("Name:", self.category_name)
        form_layout.addRow("Description:", self.category_description)

        # Buttons
        btn_layout = QHBoxLayout()
        add_cat_btn = QPushButton("Add Category")
        add_cat_btn.clicked.connect(self.add_category)
        update_cat_btn = QPushButton("Update Category")
        update_cat_btn.clicked.connect(self.update_category)
        delete_cat_btn = QPushButton("Delete Category")
        delete_cat_btn.clicked.connect(self.delete_category)
        delete_cat_btn.setStyleSheet("QPushButton { background-color: #f44336; }")
        clear_cat_btn = QPushButton("Clear Form") # New clear button
        clear_cat_btn.clicked.connect(self.clear_category_form)

        btn_layout.addWidget(add_cat_btn)
        btn_layout.addWidget(update_cat_btn)
        btn_layout.addWidget(delete_cat_btn)
        btn_layout.addWidget(clear_cat_btn)

        form_layout.addRow(btn_layout)
        form_group.setLayout(form_layout)

        layout.addWidget(self.categories_list)
        layout.addWidget(form_group)

        widget.setLayout(layout)
        return widget

    def create_reports_tab(self):
        """Create reports tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Report buttons
        report_layout = QHBoxLayout()

        low_stock_btn = QPushButton("Low Stock Report")
        low_stock_btn.clicked.connect(self.generate_low_stock_report)

        inventory_btn = QPushButton("Full Inventory Report")
        inventory_btn.clicked.connect(self.generate_inventory_report)

        category_btn = QPushButton("Category Report")
        category_btn.clicked.connect(self.generate_category_report)

        report_layout.addWidget(low_stock_btn)
        report_layout.addWidget(inventory_btn)
        report_layout.addWidget(category_btn)

        # Report display
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        self.report_display.setFont(QFont("Consolas", 10)) # Monospace font for reports

        layout.addLayout(report_layout)
        layout.addWidget(self.report_display)

        widget.setLayout(layout)
        return widget

    def refresh_all_data(self):
        """Refresh all data in the application"""
        self.load_categories() # Ensure categories are loaded first as items depend on them
        self.load_items()
        self.update_dashboard()
        self.statusBar().showMessage("Data refreshed", 2000)

    def load_items(self):
        """Load items into the table"""
        items = self.db_manager.execute_query("""
            SELECT i.id, i.name, c.name AS category_name, i.quantity, i.price, i.min_stock, i.supplier, i.date_added
            FROM items i LEFT JOIN categories c ON i.category_id = c.id
            ORDER BY i.id ASC
        """, fetch=True)

        self.items_table.setRowCount(len(items) if items else 0)

        if items:
            for row, item_data in enumerate(items):
                # Ensure values are robust to None for display
                item_id = str(item_data['id'])
                item_name = str(item_data['name'] or "")
                category_name = str(item_data['category_name'] or "N/A")
                quantity = int(item_data['quantity'] or 0)
                price = float(item_data['price'] or 0.0)
                min_stock = int(item_data['min_stock'] or 0)
                supplier = str(item_data['supplier'] or "")
                date_added = str(item_data['date_added'] or "")

                self.items_table.setItem(row, 0, QTableWidgetItem(item_id))
                self.items_table.setItem(row, 1, QTableWidgetItem(item_name))
                self.items_table.setItem(row, 2, QTableWidgetItem(category_name))
                self.items_table.setItem(row, 3, QTableWidgetItem(str(quantity)))
                self.items_table.setItem(row, 4, QTableWidgetItem(f"${price:.2f}"))
                self.items_table.setItem(row, 5, QTableWidgetItem(str(min_stock)))
                self.items_table.setItem(row, 6, QTableWidgetItem(supplier))
                self.items_table.setItem(row, 7, QTableWidgetItem(date_added))

                # Highlight low stock items
                if quantity <= min_stock:
                    for col in range(self.items_table.columnCount()):
                        self.items_table.item(row, col).setBackground(QColor(255, 220, 220)) # Lighter red highlight
                else:
                    # Clear background if it was previously highlighted
                    for col in range(self.items_table.columnCount()):
                        # Check if row is even or odd for alternating background
                        if row % 2 == 0:
                            self.items_table.item(row, col).setBackground(QColor(Qt.white))
                        else:
                            self.items_table.item(row, col).setBackground(QColor("#f9f9f9"))

        self.items_table.resizeColumnsToContents() # Auto-adjust column widths
        self.items_table.resizeRowsToContents()

    def load_item_details_to_form(self, item):
        """Load selected item details into the form for editing."""
        row = item.row()
        item_id = self.items_table.item(row, 0).text()
        item_name = self.items_table.item(row, 1).text()
        category_name = self.items_table.item(row, 2).text()
        quantity = int(self.items_table.item(row, 3).text())
        price_str = self.items_table.item(row, 4).text().replace('$', '') # Remove '$'
        price = float(price_str)
        min_stock = int(self.items_table.item(row, 5).text())
        supplier = self.items_table.item(row, 6).text()

        self.item_name.setText(item_name)
        # Set category dropdown
        index = self.item_category.findText(category_name, Qt.MatchExactly)
        if index == -1 and category_name == "N/A":
            index = self.item_category.findData(0) # Find the "Select Category" or 0 ID
            if index == -1: # Fallback if "Select Category" isn't present
                index = 0
        if index != -1:
            self.item_category.setCurrentIndex(index)
        else:
            self.item_category.setCurrentIndex(0) # Default to first item if not found

        self.item_quantity.setValue(quantity)
        self.item_price.setValue(price)
        self.item_min_stock.setValue(min_stock)
        self.item_supplier.setText(supplier)


    def load_categories(self):
        """Load categories into dropdowns and lists"""
        categories = self.db_manager.execute_query("SELECT id, name FROM categories ORDER BY name ASC", fetch=True)

        # Update category dropdown in items form
        self.item_category.clear()
        self.item_category.addItem("Select Category", 0) # Value 0 for no category selected
        if categories:
            for cat_data in categories:
                self.item_category.addItem(cat_data['name'], cat_data['id'])

        # Update category filter
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        if categories:
            for cat_data in categories:
                self.category_filter.addItem(cat_data['name'])

        # Update categories list
        self.categories_list.clear()
        if categories:
            for cat_data in categories:
                list_item = QListWidgetItem(cat_data['name'])
                list_item.setData(Qt.UserRole, cat_data['id'])
                self.categories_list.addItem(list_item)


    def update_dashboard(self):
        """Update dashboard statistics and chart"""
        # Update total items card
        total_items_count = self.db_manager.execute_query("SELECT COUNT(*) FROM items", fetch=True)[0][0]
        # Access the QLabel inside the stat card by its object name
        self.total_items_card.findChild(QLabel, "statValueLabel_totalItemsLabel").setText(str(total_items_count))

        # Update low stock items card
        low_stock_count = self.db_manager.execute_query(
            "SELECT COUNT(*) FROM items WHERE quantity <= min_stock", fetch=True)[0][0]
        self.low_stock_card.findChild(QLabel, "statValueLabel_lowStockLabel").setText(str(low_stock_count))

        # Update total categories card
        total_categories_count = self.db_manager.execute_query("SELECT COUNT(*) FROM categories", fetch=True)[0][0]
        self.categories_card.findChild(QLabel, "statValueLabel_categoriesLabel").setText(str(total_categories_count))

        # Update chart with current stock levels (Top 10 lowest stock)
        items_data = self.db_manager.execute_query(
            "SELECT name, quantity FROM items ORDER BY quantity ASC LIMIT 10", fetch=True)

        # Convert sqlite3.Row objects to tuples for chart
        if items_data:
            chart_data = [(item['name'], item['quantity']) for item in items_data]
            self.chart_widget.plot_stock_levels(chart_data)
        else:
            self.chart_widget.plot_stock_levels([]) # Clear chart if no data

    def filter_items(self):
        """Filter items based on search and category"""
        search_text = self.search_input.text().lower()
        category_text = self.category_filter.currentText()

        for row in range(self.items_table.rowCount()):
            show_row = True

            # Check search text
            if search_text:
                item_name = self.items_table.item(row, 1).text().lower()
                if search_text not in item_name:
                    show_row = False

            # Check category filter
            if category_text != "All Categories":
                item_category = self.items_table.item(row, 2).text()
                if category_text != item_category:
                    show_row = False

            self.items_table.setRowHidden(row, not show_row)

    def add_item(self):
        """Add new item to inventory"""
        item_name = self.item_name.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Error", "Item name is required!")
            return

        category_id = self.item_category.currentData()
        # Allows adding items without a category (category_id 0 or NULL)

        try:
            self.db_manager.execute_query("""
                INSERT INTO items (name, category_id, quantity, price, min_stock, supplier, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item_name,
                category_id if category_id != 0 else None, # Store None if "Select Category" is chosen
                self.item_quantity.value(),
                self.item_price.value(),
                self.item_min_stock.value(),
                self.item_supplier.text().strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            self.clear_item_form()
            self.load_items()
            self.update_dashboard()
            QMessageBox.information(self, "Success", "Item added successfully!")
        except sqlite3.IntegrityError as e:
            # You might want to handle unique item names, but it's less common for items
            QMessageBox.warning(self, "Duplicate Item", f"An item with the name '{item_name}' might already exist, or another integrity error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add item: {e}")

    def update_item(self):
        """Update selected item"""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Please select an item to update!")
            return

        item_id = self.items_table.item(current_row, 0).text()
        item_name = self.item_name.text().strip()
        category_id = self.item_category.currentData() # Will be 0 if "Select Category" is chosen

        if not item_name:
            QMessageBox.warning(self, "Error", "Item name is required!")
            return

        try:
            self.db_manager.execute_query("""
                UPDATE items SET name=?, category_id=?, quantity=?, price=?, min_stock=?, supplier=?
                WHERE id=?
            """, (
                item_name,
                category_id if category_id != 0 else None, # Store None if "Select Category" is chosen
                self.item_quantity.value(),
                self.item_price.value(),
                self.item_min_stock.value(),
                self.item_supplier.text().strip(),
                item_id
            ))

            self.clear_item_form()
            self.load_items()
            self.update_dashboard()
            QMessageBox.information(self, "Success", "Item updated successfully!")
        except sqlite3.IntegrityError as e:
             QMessageBox.warning(self, "Duplicate Item", f"An item with the name '{item_name}' might already exist, or another integrity error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update item: {e}")

    def delete_item(self):
        """Delete selected item"""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Please select an item to delete!")
            return

        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this item?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            item_id = self.items_table.item(current_row, 0).text()
            try:
                self.db_manager.execute_query("DELETE FROM items WHERE id=?", (item_id,))
                self.clear_item_form()
                self.load_items()
                self.update_dashboard()
                QMessageBox.information(self, "Success", "Item deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete item: {e}")

    def clear_item_form(self):
        """Clear item form fields"""
        self.item_name.clear()
        self.item_category.setCurrentIndex(0) # Set to "Select Category"
        self.item_quantity.setValue(0)
        self.item_price.setValue(0.00)
        self.item_min_stock.setValue(0)
        self.item_supplier.clear()
        self.items_table.clearSelection() # Clear selection in table

    def add_category(self):
        """Add new category"""
        category_name = self.category_name.text().strip() # Use .strip() to remove whitespace
        if not category_name:
            QMessageBox.warning(self, "Error", "Category name is required!")
            return

        try:
            self.db_manager.execute_query(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (category_name, self.category_description.toPlainText().strip())
            )
            self.clear_category_form()
            self.load_categories()
            self.update_dashboard()
            QMessageBox.information(self, "Success", "Category added successfully!")
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: categories.name" in str(e):
                QMessageBox.warning(self, "Duplicate Category",
                                    f"Category '{category_name}' already exists. Please choose a unique name.")
            else:
                QMessageBox.critical(self, "Database Error", f"An integrity error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add category: {e}")

    def update_category(self):
        """Update selected category"""
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a category to update!")
            return

        cat_id = current_item.data(Qt.UserRole)
        category_name = self.category_name.text().strip()
        if not category_name:
            QMessageBox.warning(self, "Error", "Category name cannot be empty!")
            return

        try:
            self.db_manager.execute_query(
                "UPDATE categories SET name=?, description=? WHERE id=?",
                (category_name, self.category_description.toPlainText().strip(), cat_id)
            )
            self.clear_category_form()
            self.load_categories()
            self.load_items() # Important: Item category names might change if updated
            self.update_dashboard()
            QMessageBox.information(self, "Success", "Category updated successfully!")
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: categories.name" in str(e):
                QMessageBox.warning(self, "Duplicate Category",
                                    f"Category '{category_name}' already exists. Please choose a unique name.")
            else:
                QMessageBox.critical(self, "Database Error", f"An integrity error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update category: {e}")

    def delete_category(self):
        """Delete selected category"""
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a category to delete!")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this category? Items previously assigned to this category will become 'Uncategorized'.",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            cat_id = current_item.data(Qt.UserRole)
            try:
                # The ON DELETE SET NULL constraint in the database schema handles this automatically.
                # No manual UPDATE items query needed here.
                self.db_manager.execute_query("DELETE FROM categories WHERE id=?", (cat_id,))

                self.clear_category_form()
                self.load_categories()
                self.load_items()      # Items will need to refresh as their category might be gone
                self.update_dashboard()
                QMessageBox.information(self, "Success", "Category deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete category: {e}")

    def clear_category_form(self):
        """Clear category form fields"""
        self.category_name.clear()
        self.category_description.clear()
        self.categories_list.clearSelection() # Clear selection in list

    def load_category_details(self, item):
        """Load category details into form"""
        cat_id = item.data(Qt.UserRole)
        try:
            category_data = self.db_manager.execute_query(
                "SELECT name, description FROM categories WHERE id=?", (cat_id,), fetch=True)

            if category_data:
                # SQLite row_factory returns rows that can be accessed by column name
                self.category_name.setText(category_data[0]['name'])
                self.category_description.setPlainText(category_data[0]['description'] or "")
            else:
                self.clear_category_form() # Clear if item somehow not found
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load category details: {e}")
            self.clear_category_form()


    def generate_low_stock_report(self):
        """Generate low stock report"""
        items = self.db_manager.execute_query("""
            SELECT i.name, c.name AS category_name, i.quantity, i.min_stock
            FROM items i LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity <= i.min_stock
            ORDER BY i.quantity ASC
        """, fetch=True)

        report = "LOW STOCK REPORT\n" + "="*50 + "\n\n"

        if items:
            for item_data in items: # Use item_data as dict/row
                report += f"Item: {item_data['name']}\n"
                report += f"Category: {item_data['category_name'] or 'N/A'}\n" # Corrected to item_data['category_name']
                report += f"Current Stock: {item_data['quantity']}\n"
                report += f"Minimum Stock: {item_data['min_stock']}\n"
                report += "-" * 30 + "\n"
        else:
            report += "No items are currently low in stock.\n"

        self.report_display.setText(report)

    def generate_inventory_report(self):
        """Generate full inventory report"""
        items = self.db_manager.execute_query("""
            SELECT i.name, c.name AS category_name, i.quantity, i.price, i.supplier
            FROM items i LEFT JOIN categories c ON i.category_id = c.id
            ORDER BY i.name
        """, fetch=True)

        report = "FULL INVENTORY REPORT\n" + "="*50 + "\n\n"
        total_value = 0

        if items:
            for item_data in items: # Use item_data as dict/row
                value = (item_data['quantity'] or 0) * (item_data['price'] or 0)
                total_value += value

                report += f"Item: {item_data['name']}\n"
                report += f"Category: {item_data['category_name'] or 'N/A'}\n"
                report += f"Quantity: {item_data['quantity'] or 0}\n"
                report += f"Price: ${item_data['price'] or 0:.2f}\n"
                report += f"Total Value: ${value:.2f}\n"
                report += f"Supplier: {item_data['supplier'] or 'N/A'}\n"
                report += "-" * 30 + "\n"

            report += f"\nTOTAL INVENTORY VALUE: ${total_value:.2f}\n"
        else:
            report += "No items in inventory.\n"

        self.report_display.setText(report)

    def generate_category_report(self):
        """Generate category-wise report"""
        categories = self.db_manager.execute_query("""
            SELECT c.name, COUNT(i.id) as item_count, SUM(i.quantity * i.price) as total_value
            FROM categories c LEFT JOIN items i ON c.id = i.category_id
            GROUP BY c.id, c.name
            ORDER BY total_value DESC
        """, fetch=True)

        report = "CATEGORY REPORT\n" + "="*50 + "\n\n"

        if categories:
            for cat_data in categories: # Use cat_data as dict/row
                report += f"Category: {cat_data['name']}\n"
                report += f"Number of Items: {cat_data['item_count'] or 0}\n"
                report += f"Total Value: ${cat_data['total_value'] or 0:.2f}\n"
                report += "-" * 30 + "\n"
        else:
            report += "No categories found.\n"

        self.report_display.setText(report)

    def export_to_excel(self):
        """Export inventory data to Excel"""
        try:
            items = self.db_manager.execute_query("""
                SELECT i.name, c.name AS category_name, i.quantity, i.price, i.min_stock, i.supplier, i.date_added
                FROM items i LEFT JOIN categories c ON i.category_id = c.id
            """, fetch=True)

            if not items:
                QMessageBox.warning(self, "Warning", "No data to export!")
                return

            # Convert list of sqlite3.Row objects to list of lists for DataFrame
            data_for_df = []
            for item_row in items:
                data_for_df.append([
                    item_row['name'],
                    item_row['category_name'] or 'N/A',
                    item_row['quantity'],
                    item_row['price'],
                    item_row['min_stock'],
                    item_row['supplier'],
                    item_row['date_added']
                ])

            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", "inventory_export.xlsx", "Excel Files (*.xlsx)")

            if filename:
                df = pd.DataFrame(data_for_df, columns=[
                    'Item Name', 'Category', 'Quantity', 'Price', 'Min Stock', 'Supplier', 'Date Added'
                ])
                df.to_excel(filename, index=False)
                QMessageBox.information(self, "Success", f"Data exported to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def export_to_pdf(self):
        """Export inventory data to PDF"""
        try:
            items = self.db_manager.execute_query("""
                SELECT i.name, c.name AS category_name, i.quantity, i.price, i.min_stock, i.supplier
                FROM items i LEFT JOIN categories c ON i.category_id = c.id
                ORDER BY i.name
            """, fetch=True)

            if not items:
                QMessageBox.warning(self, "Warning", "No data to export!")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "Save PDF File", "inventory_report.pdf", "PDF Files (*.pdf)")

            if filename:
                c = canvas.Canvas(filename, pagesize=letter)
                width, height = letter
                margin = 50
                line_height = 16
                y_position = height - margin

                # Title
                c.setFont("Helvetica-Bold", 18)
                c.drawString(margin, y_position, "Inventory Report")
                y_position -= line_height

                c.setFont("Helvetica", 10)
                c.drawString(margin, y_position, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                y_position -= (line_height * 2)

                # Headers
                c.setFont("Helvetica-Bold", 10)
                headers = ["Item", "Category", "Qty", "Price", "Min Stock", "Supplier"]
                # Adjust x_positions based on your data and preferred column width
                x_positions = [margin, margin + 100, margin + 200, margin + 250, margin + 300, margin + 380]

                for i, header in enumerate(headers):
                    c.drawString(x_positions[i], y_position, header)
                y_position -= line_height

                c.line(margin, y_position, width - margin, y_position) # Draw a line under headers
                y_position -= line_height # Space after header line

                # Data
                c.setFont("Helvetica", 9)
                row_count = 0
                # Calculate max_rows_per_page dynamically based on available space
                # (height - top_margin - bottom_margin - header_block_height) / line_height
                max_rows_per_page = int((height - (margin * 2) - (line_height * 4)) / line_height) # Estimate

                for item_data in items:
                    if y_position < margin: # Check if new page is needed
                        c.showPage() # Start new page
                        y_position = height - margin # Reset y_position for new page
                        c.setFont("Helvetica-Bold", 10)
                        for i, header in enumerate(headers):
                            c.drawString(x_positions[i], y_position, header)
                        y_position -= line_height
                        c.line(margin, y_position, width - margin, y_position)
                        y_position -= line_height
                        c.setFont("Helvetica", 9) # Reset font for data

                    item_name = item_data['name'] or ""
                    category_name = item_data['category_name'] or "N/A"
                    quantity = str(item_data['quantity'] or 0)
                    price = f"${item_data['price'] or 0:.2f}"
                    min_stock = str(item_data['min_stock'] or 0)
                    supplier = item_data['supplier'] or ""

                    # Draw item data
                    c.drawString(x_positions[0], y_position, item_name)
                    c.drawString(x_positions[1], y_position, category_name)
                    c.drawString(x_positions[2], y_position, quantity)
                    c.drawString(x_positions[3], y_position, price)
                    c.drawString(x_positions[4], y_position, min_stock)
                    c.drawString(x_positions[5], y_position, supplier)

                    y_position -= line_height
                    row_count += 1

                c.save() # Save the PDF file
                QMessageBox.information(self, "Success", f"Data exported to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"PDF export failed: {str(e)}")

    def logout(self):
        """Handle user logout"""
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to log out?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.hide() # Hide the main window
            self.current_user_role = None # Clear role
            # Re-open login dialog or exit
            login_dialog = LoginDialog(self.db_manager)
            if login_dialog.exec_() == QDialog.Accepted:
                self.current_user_role = login_dialog.user_role
                self.show() # Show main window again with new session
                self.statusBar().showMessage(f"Logged in as: {self.current_user_role.capitalize()}")
                self.refresh_all_data() # Refresh UI for new session
            else:
                sys.exit() # Exit if user cancels login

# Main application entry point
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InventoryApp()
    window.show()
    sys.exit(app.exec_())
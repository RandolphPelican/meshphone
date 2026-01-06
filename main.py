"""
MeshPhone - Mobile App Entry Point
Real Kivy application for Android/iOS
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

import time
from meshphone.mesh_app import MeshPhoneApp, AppConfig


# Set window size for desktop testing
if platform not in ('android', 'ios'):
    Window.size = (400, 700)


class ContactCard(BoxLayout):
    """A contact card in the list"""
    
    def __init__(self, contact_id, display_name, last_message="", is_online=False, unread_count=0, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 80
        self.padding = 10
        self.spacing = 10
        
        self.contact_id = contact_id
        
        # Status indicator
        status_color = [0, 1, 0, 1] if is_online else [0.5, 0.5, 0.5, 1]
        status = Label(
            text='●',
            size_hint_x=0.1,
            color=status_color,
            font_size='20sp'
        )
        
        # Contact info
        info_layout = BoxLayout(orientation='vertical', size_hint_x=0.7)
        name_label = Label(
            text=display_name,
            size_hint_y=0.5,
            halign='left',
            valign='middle',
            font_size='18sp',
            bold=True
        )
        name_label.bind(size=name_label.setter('text_size'))
        
        message_label = Label(
            text=last_message[:50] if last_message else 'No messages yet',
            size_hint_y=0.5,
            halign='left',
            valign='middle',
            font_size='14sp',
            color=[0.6, 0.6, 0.6, 1]
        )
        message_label.bind(size=message_label.setter('text_size'))
        
        info_layout.add_widget(name_label)
        info_layout.add_widget(message_label)
        
        # Unread badge
        unread = Label(
            text=str(unread_count) if unread_count > 0 else '',
            size_hint_x=0.2,
            font_size='16sp',
            color=[1, 1, 1, 1] if unread_count > 0 else [0, 0, 0, 0]
        )
        
        self.add_widget(status)
        self.add_widget(info_layout)
        self.add_widget(unread)


class MessageBubble(BoxLayout):
    """A message bubble in the chat"""
    
    def __init__(self, content, is_outgoing, timestamp, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.padding = 10
        self.spacing = 5
        
        # Calculate height based on content
        self.height = max(60, len(content) // 30 * 20 + 40)
        
        # Time label
        dt = time.localtime(timestamp)
        time_str = time.strftime("%H:%M", dt)
        
        if is_outgoing:
            # Sent message (right aligned, blue)
            spacer = Label(size_hint_x=0.3)
            bubble = Label(
                text=f"{content}\n{time_str}",
                size_hint_x=0.7,
                halign='right',
                valign='middle',
                color=[1, 1, 1, 1],
                font_size='16sp'
            )
            bubble.bind(size=bubble.setter('text_size'))
            
            self.add_widget(spacer)
            self.add_widget(bubble)
        else:
            # Received message (left aligned, gray)
            bubble = Label(
                text=f"{content}\n{time_str}",
                size_hint_x=0.7,
                halign='left',
                valign='middle',
                color=[0, 0, 0, 1],
                font_size='16sp'
            )
            bubble.bind(size=bubble.setter('text_size'))
            spacer = Label(size_hint_x=0.3)
            
            self.add_widget(bubble)
            self.add_widget(spacer)


class ContactsScreen(Screen):
    """Contact list screen"""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.name = 'contacts'
        self.app_instance = app_instance
        
        layout = BoxLayout(orientation='vertical')
        
        # Header
        header = BoxLayout(size_hint_y=0.1, padding=10)
        title = Label(text='MeshPhone', font_size='24sp', bold=True)
        settings_btn = Button(text='⚙', size_hint_x=0.2, font_size='20sp')
        settings_btn.bind(on_press=self.open_settings)
        
        header.add_widget(title)
        header.add_widget(settings_btn)
        
        # Status bar
        self.status_bar = Label(
            text='📶 Connecting...',
            size_hint_y=0.05,
            font_size='14sp',
            color=[0.6, 0.6, 0.6, 1]
        )
        
        # Contact list
        scroll = ScrollView(size_hint_y=0.85)
        self.contact_list = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.contact_list.bind(minimum_height=self.contact_list.setter('height'))
        scroll.add_widget(self.contact_list)
        
        layout.add_widget(header)
        layout.add_widget(self.status_bar)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        # Schedule updates
        Clock.schedule_interval(self.update_contacts, 2.0)
    
    def open_settings(self, instance):
        """Open settings screen"""
        self.manager.transition.direction = 'left'
        self.manager.current = 'settings'
    
    def update_contacts(self, dt):
        """Update contact list from backend"""
        self.contact_list.clear_widgets()
        
        # Update status
        if self.app_instance.backend:
            status = self.app_instance.backend.get_status()
            self.status_bar.text = f"📶 {status.mode.title()} • {status.mesh_neighbors} neighbors • {status.energy_balance:.0f}j"
        
        # Add contacts
        for contact in self.app_instance.contacts:
            card = ContactCard(
                contact_id=contact['id'],
                display_name=contact['name'],
                last_message=contact.get('last_message', ''),
                is_online=contact.get('is_online', False),
                unread_count=contact.get('unread', 0)
            )
            card.bind(on_touch_down=lambda instance, touch, cid=contact['id']: self.open_chat(cid) if instance.collide_point(*touch.pos) else None)
            self.contact_list.add_widget(card)
    
    def open_chat(self, contact_id):
        """Open chat with contact"""
        self.manager.get_screen('chat').load_chat(contact_id)
        self.manager.transition.direction = 'left'
        self.manager.current = 'chat'


class ChatScreen(Screen):
    """Chat conversation screen"""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.name = 'chat'
        self.app_instance = app_instance
        self.current_contact = None
        
        layout = BoxLayout(orientation='vertical')
        
        # Header
        header = BoxLayout(size_hint_y=0.08, padding=10)
        back_btn = Button(text='←', size_hint_x=0.15, font_size='24sp')
        back_btn.bind(on_press=self.go_back)
        self.contact_name = Label(text='', font_size='20sp', bold=True)
        header.add_widget(back_btn)
        header.add_widget(self.contact_name)
        
        # Messages
        scroll = ScrollView(size_hint_y=0.82)
        self.message_list = GridLayout(cols=1, spacing=5, size_hint_y=None, padding=10)
        self.message_list.bind(minimum_height=self.message_list.setter('height'))
        scroll.add_widget(self.message_list)
        
        # Input area
        input_layout = BoxLayout(size_hint_y=0.1, padding=5, spacing=5)
        self.message_input = TextInput(
            hint_text='Type a message...',
            multiline=False,
            font_size='16sp'
        )
        send_btn = Button(text='Send', size_hint_x=0.25, font_size='18sp')
        send_btn.bind(on_press=self.send_message)
        
        input_layout.add_widget(self.message_input)
        input_layout.add_widget(send_btn)
        
        layout.add_widget(header)
        layout.add_widget(scroll)
        layout.add_widget(input_layout)
        
        self.add_widget(layout)
    
    def load_chat(self, contact_id):
        """Load chat with a contact"""
        self.current_contact = contact_id
        
        # Find contact name
        contact = next((c for c in self.app_instance.contacts if c['id'] == contact_id), None)
        if contact:
            self.contact_name.text = contact['name']
        
        # Load messages
        self.message_list.clear_widgets()
        messages = self.app_instance.get_messages(contact_id)
        
        for msg in messages:
            bubble = MessageBubble(
                content=msg['content'],
                is_outgoing=msg['is_outgoing'],
                timestamp=msg['timestamp']
            )
            self.message_list.add_widget(bubble)
    
    def send_message(self, instance):
        """Send a message"""
        content = self.message_input.text.strip()
        if not content or not self.current_contact:
            return
        
        # Send via backend
        success = self.app_instance.send_message(self.current_contact, content)
        
        if success:
            # Add to UI
            bubble = MessageBubble(
                content=content,
                is_outgoing=True,
                timestamp=time.time()
            )
            self.message_list.add_widget(bubble)
            self.message_input.text = ''
    
    def go_back(self, instance):
        """Go back to contact list"""
        self.manager.transition.direction = 'right'
        self.manager.current = 'contacts'


class SettingsScreen(Screen):
    """Settings screen"""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        self.app_instance = app_instance
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(size_hint_y=0.08)
        back_btn = Button(text='←', size_hint_x=0.15, font_size='24sp')
        back_btn.bind(on_press=self.go_back)
        title = Label(text='Settings', font_size='24sp', bold=True)
        header.add_widget(back_btn)
        header.add_widget(title)
        
        # Settings content
        scroll = ScrollView()
        settings_layout = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        settings_layout.bind(minimum_height=settings_layout.setter('height'))
        
        # Free Mode toggle
        free_mode = BoxLayout(size_hint_y=None, height=60)
        free_label = Label(text='Free Mode\nUse mesh instead of carrier', font_size='16sp', halign='left')
        free_label.bind(size=free_label.setter('text_size'))
        self.free_toggle = Button(text='ON', size_hint_x=0.3, font_size='18sp', background_color=[0.2, 0.8, 0.2, 1])
        self.free_toggle.bind(on_press=self.toggle_free_mode)
        free_mode.add_widget(free_label)
        free_mode.add_widget(self.free_toggle)
        
        # Stats
        self.stats_label = Label(
            text='Loading stats...',
            size_hint_y=None,
            height=200,
            font_size='14sp',
            halign='left',
            valign='top'
        )
        self.stats_label.bind(size=self.stats_label.setter('text_size'))
        
        settings_layout.add_widget(free_mode)
        settings_layout.add_widget(Label(text='', size_hint_y=None, height=20))
        settings_layout.add_widget(self.stats_label)
        
        scroll.add_widget(settings_layout)
        
        layout.add_widget(header)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        # Update stats
        Clock.schedule_interval(self.update_stats, 2.0)
    
    def update_stats(self, dt):
        """Update statistics"""
        if self.app_instance.backend:
            stats = self.app_instance.backend.get_stats()
            
            self.stats_label.text = f"""📊 NETWORK STATISTICS

Mesh Neighbors: {stats['mesh_neighbors']}
Messages Sent: {stats['messages_sent']}
Messages Relayed: {stats['messages_relayed']}

Energy Balance: {stats['energy_balance']:.0f}j

💰 SAVINGS
Carrier cost: $0.00
vs AT&T: $100/month
Annual savings: $1200"""
    
    def toggle_free_mode(self, instance):
        """Toggle free mode"""
        if self.free_toggle.text == 'ON':
            self.free_toggle.text = 'OFF'
            self.free_toggle.background_color = [0.8, 0.2, 0.2, 1]
        else:
            self.free_toggle.text = 'ON'
            self.free_toggle.background_color = [0.2, 0.8, 0.2, 1]
    
    def go_back(self, instance):
        """Go back to contacts"""
        self.manager.transition.direction = 'right'
        self.manager.current = 'contacts'


class MeshPhoneKivyApp(App):
    """Main Kivy application"""
    
    def build(self):
        self.title = 'MeshPhone'
        
        # Initialize backend
        self.config = AppConfig(
            node_id='user_001',
            display_name='User',
            free_mode_enabled=True
        )
        self.backend = MeshPhoneApp(self.config)
        self.backend.initialize()
        self.backend.start()
        
        # Mock contacts for testing
        self.contacts = [
            {'id': 'alice_001', 'name': 'Alice', 'is_online': True, 'unread': 0, 'last_message': ''},
            {'id': 'bob_002', 'name': 'Bob', 'is_online': False, 'unread': 0, 'last_message': ''}
        ]
        
        self.messages = {}
        
        # Create screen manager
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(ContactsScreen(self))
        sm.add_widget(ChatScreen(self))
        sm.add_widget(SettingsScreen(self))
        
        return sm
    
    def send_message(self, contact_id, content):
        """Send a message via backend"""
        success = self.backend.send_message(contact_id, content)
        
        if success:
            # Store in UI
            if contact_id not in self.messages:
                self.messages[contact_id] = []
            
            self.messages[contact_id].append({
                'content': content,
                'is_outgoing': True,
                'timestamp': time.time()
            })
            
            # Update contact last message
            for contact in self.contacts:
                if contact['id'] == contact_id:
                    contact['last_message'] = content[:50]
        
        return success
    
    def get_messages(self, contact_id):
        """Get messages for a contact"""
        return self.messages.get(contact_id, [])
    
    def on_stop(self):
        """Cleanup when app closes"""
        if self.backend:
            self.backend.stop()


if __name__ == '__main__':
    MeshPhoneKivyApp().run()

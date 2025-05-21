from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню админ-панели
admin_main = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [
            InlineKeyboardButton(text="🎁 Создать промокод", callback_data="create_promo"),
            InlineKeyboardButton(text="🔗 Создать реф. ссылку", callback_data="create_ref_link")
        ],
        [
            InlineKeyboardButton(text="📋 Мои реф. ссылки", callback_data="show_ref_links"),
            InlineKeyboardButton(text="📢 ОП каналы", callback_data="op_channels")
        ],
        [InlineKeyboardButton(text="📝 Каналы заданий", callback_data="task_channels")],
        [InlineKeyboardButton(text="📢 Показы", callback_data="ad_posts")],
        [InlineKeyboardButton(text="💰 Изменить награду за реферала", callback_data="change_referral_reward")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")]],
)

# Клавиатура для статистики
admin_stats = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
])

# Клавиатура для отмены создания промокода
promo_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_promo_creation")]
])

# Клавиатура для отмены создания реферальной ссылки
ref_link_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ref_link_creation")]
])

# Клавиатура для ОП каналов
op_channels_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁 Посмотреть", callback_data="op_channels_list")],
    [InlineKeyboardButton(text="➕ Добавить", callback_data="op_channel_add")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
])

# Меню управления каналами заданий
task_channels_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👁 Посмотреть", callback_data="task_channels_list"),
            InlineKeyboardButton(text="➕ Добавить", callback_data="task_channel_add")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ]
)

def get_ref_links_keyboard(links: list, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для отображения реферальных ссылок с пагинацией
    
    Args:
        links (list): Список ссылок для текущей страницы
        page (int): Текущая страница (начиная с 0)
        total_pages (int): Общее количество страниц
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с ссылками и кнопками навигации
    """
    keyboard = []
    
    # Добавляем кнопки для каждой ссылки
    for link in links:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{link['name']} ({link['uses_count']} 👥)",
                callback_data=f"ref_link_{link['id']}"
            )
        ])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    
    # Кнопка "Предыдущая страница"
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"ref_links_page_{page-1}")
        )
    
    # Информация о текущей странице
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"📄 {page+1}/{total_pages}",
            callback_data="ignore"  # Игнорируем нажатие на эту кнопку
        )
    )
    
    # Кнопка "Следующая страница"
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"ref_links_page_{page+1}")
        )
    
    keyboard.append(nav_buttons)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ref_link_details_keyboard(link_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для отображения деталей реферальной ссылки
    
    Args:
        link_id (int): ID реферальной ссылки
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"ref_link_{link_id}"),
            InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"ref_link_deactivate_{link_id}")
        ],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="show_ref_links")]
    ])

def get_op_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком ОП каналов
    
    Args:
        channels (list): Список каналов
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с каналами и кнопкой "Назад"
    """
    keyboard = []
    
    # Добавляем кнопки для каждого канала
    for channel in channels:
        status = "✅" if channel['is_active'] else "❌"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {channel['name']}",
                callback_data=f"op_channel_{channel['id']}"
            )
        ])
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="op_channels")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_op_channel_details_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления конкретным ОП каналом
    
    Args:
        channel_id (int): ID канала
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"op_channel_delete_{channel_id}"),
            InlineKeyboardButton(text="🔄 Изменить статус", callback_data=f"op_channel_toggle_{channel_id}")
        ],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="op_channels_list")]
    ])

# Клавиатура для отмены добавления ОП канала
op_channel_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="op_channels")]
])

def get_task_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком каналов заданий"""
    keyboard = []
    for channel in channels:
        status = "✅" if channel['is_active'] else "❌"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {channel['name']} ({channel['completed_count']}/{channel['total_limit']})",
                callback_data=f"task_channel_{channel['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="task_channels")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_task_channel_details_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления конкретным каналом заданий"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"task_channel_delete_{channel_id}"),
                InlineKeyboardButton(text="🔄 Статус", callback_data=f"task_channel_toggle_{channel_id}")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="task_channels_list")]
        ]
    )

# Клавиатура для отмены добавления канала заданий
task_channel_cancel = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task_channel_creation")]
    ]
)

# Клавиатура для отмены изменения награды за реферала
referral_reward_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_referral_reward_change")]
])

# Меню управления рекламными постами
ad_posts_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👁 Посмотреть", callback_data="ad_posts_list"),
            InlineKeyboardButton(text="➕ Добавить", callback_data="ad_post_add")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ]
)

def get_ad_posts_keyboard(posts: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком рекламных постов"""
    keyboard = []
    for post in posts:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{post['name']} ({post['show_count']} 👁)",
                callback_data=f"ad_post_{post['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="ad_posts")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ad_post_details_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления конкретным рекламным постом"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"_delete_{post_id}")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ad_posts_list")]
        ]
    )

# Клавиатура для отмены добавления рекламного поста
ad_post_cancel = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad_post_creation")]
    ]
)




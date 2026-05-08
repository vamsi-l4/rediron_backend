"""
Django management command to populate sample equipment data for Equipment Detail Page
Usage: python manage.py populate_equipment_data
"""

from django.core.management.base import BaseCommand
from rediron_shop.models import Category, Product, ProductImage
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Populate sample equipment data for demonstration'

    def handle(self, *args, **options):
        # Create categories
        categories_data = [
            {'name': 'Cardio Equipment', 'slug': 'cardio'},
            {'name': 'Strength Equipment', 'slug': 'strength'},
            {'name': 'Core Equipment', 'slug': 'core'}
        ]

        categories = {}
        for cat_data in categories_data:
            try:
                category, created = Category.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={'slug': cat_data['slug']}
                )
                # Update slug if it doesn't match
                if category.slug != cat_data['slug']:
                    category.slug = cat_data['slug']
                    category.save()
                    self.stdout.write(self.style.WARNING(f'⚠️  Updated slug for {category.name} to {cat_data["slug"]}'))
                categories[cat_data['slug']] = category
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✅ Created category: {category.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  Category already exists: {category.name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error with category {cat_data["name"]}: {e}'))
                # Try to get by slug instead
                try:
                    category = Category.objects.get(slug=cat_data['slug'])
                    categories[cat_data['slug']] = category
                    self.stdout.write(self.style.WARNING(f'⚠️  Found category by slug: {category.name}'))
                except Category.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'❌ Could not find or create category: {cat_data["name"]}'))

        # Equipment data for each category
        equipment_data = {
            'cardio': [
                {
                    'name': 'Commercial Treadmill',
                    'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'price': 199999,
                    'mrp': 250000,
                    'key_features': [
                        {'title': 'Powerful Motor', 'description': '4.0 HP Continuous / 7.0 HP Peak Performance', 'icon': 'power'},
                        {'title': 'Large Running Surface', 'description': '152 x 56 CM - Extra Wide Belt', 'icon': 'running'},
                        {'title': 'Advanced Console', 'description': 'HD Display & 20 Pre-set Programs', 'icon': 'star'},
                        {'title': 'Heart Rate Monitoring', 'description': 'Hand Sensors & Wireless Compatible', 'icon': 'heart'}
                    ],
                    'specifications': [
                        {'label': 'Motor Power', 'value': '4.0 HP Continuous / 7.0 HP Peak'},
                        {'label': 'Speed Range', 'value': '0.8 - 20 KM/H'},
                        {'label': 'Incline Range', 'value': '0 - 15%'},
                        {'label': 'Running Surface', 'value': '152 x 56 CM'},
                        {'label': 'Max User Weight', 'value': '150 KG'},
                        {'label': 'Console Display', 'value': '10.5" HD Touchscreen'},
                        {'label': 'Pre-set Programs', 'value': '20 Programs'},
                        {'label': 'Warranty', 'value': '2 Years Commercial'},
                    ],
                    'benefits': [
                        {'title': 'Commercial Grade Durability', 'description': 'Built to withstand heavy usage in commercial settings with premium components'},
                        {'title': 'Advanced Performance Tracking', 'description': 'Real-time metrics including calories, distance, heart rate, and workout data'},
                        {'title': 'Versatile Training Programs', 'description': '20 built-in programs designed by fitness experts for various fitness levels'},
                        {'title': 'Comfort & Safety', 'description': 'Cushioned running surface with emergency stop and safety rails'}
                    ],
                    'perfect_for': [
                        {'label': 'Weight Loss', 'icon': 'target'},
                        {'label': 'Endurance Training', 'icon': 'running'},
                        {'label': 'HIIT Workouts', 'icon': 'fire'},
                        {'label': 'Daily Fitness', 'icon': 'dumbbell'}
                    ],
                    'additional_stats': [
                        {'label': 'Rating', 'value': '4.5/5', 'icon': 'star'},
                        {'label': 'Max Weight', 'value': '150 KG', 'icon': 'weight'},
                        {'label': 'Speed Range', 'value': '0.8-20 KM/H', 'icon': 'speed'}
                    ]
                },
                {
                    'name': 'Spin Bike Pro',
                    'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'price': 89999,
                    'mrp': 120000,
                    'key_features': [
                        {'title': 'Magnetic Resistance', 'description': '16 Levels of Smooth Magnetic Resistance', 'icon': 'bolt'},
                        {'title': 'Ergonomic Design', 'description': 'Adjustable Seat & Handlebars', 'icon': 'star'},
                        {'title': 'Digital Console', 'description': 'LCD Display with Heart Rate Monitor', 'icon': 'heart'},
                        {'title': 'Quiet Operation', 'description': 'Belt Drive System for Silent Performance', 'icon': 'shield'}
                    ],
                    'specifications': [
                        {'label': 'Resistance System', 'value': 'Magnetic - 16 Levels'},
                        {'label': 'Drive System', 'value': 'Belt Drive'},
                        {'label': 'Flywheel Weight', 'value': '18 KG'},
                        {'label': 'Max User Weight', 'value': '120 KG'},
                        {'label': 'Console Display', 'value': 'LCD with Backlight'},
                        {'label': 'Programs', 'value': '12 Pre-set Programs'},
                        {'label': 'Dimensions', 'value': '110 x 55 x 125 CM'},
                        {'label': 'Warranty', 'value': '1 Year Commercial'},
                    ],
                    'benefits': [
                        {'title': 'Low Impact Cardio', 'description': 'Perfect for joint-friendly cardiovascular training'},
                        {'title': 'Versatile Workouts', 'description': 'Suitable for all fitness levels from beginner to advanced'},
                        {'title': 'Space Efficient', 'description': 'Compact design fits easily in home gyms'},
                        {'title': 'Motivational Training', 'description': 'Built-in programs keep workouts engaging and effective'}
                    ],
                    'perfect_for': [
                        {'label': 'Cardio Fitness', 'icon': 'heart'},
                        {'label': 'Weight Loss', 'icon': 'target'},
                        {'label': 'Endurance', 'icon': 'running'},
                        {'label': 'Home Workouts', 'icon': 'dumbbell'}
                    ],
                    'additional_stats': [
                        {'label': 'Rating', 'value': '4.3/5', 'icon': 'star'},
                        {'label': 'Max Weight', 'value': '120 KG', 'icon': 'weight'},
                        {'label': 'Resistance Levels', 'value': '16', 'icon': 'bolt'}
                    ]
                }
            ],
            'strength': [
                {
                    'name': 'Multi-Station Gym',
                    'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'price': 299999,
                    'mrp': 350000,
                    'key_features': [
                        {'title': 'Multiple Stations', 'description': 'Lat Pulldown, Chest Press, Leg Extension & More', 'icon': 'dumbbell'},
                        {'title': 'Cable System', 'description': 'Dual 160 KG Steel Weight Stack', 'icon': 'power'},
                        {'title': 'Adjustable Seats', 'description': 'Ergonomic Design for All Body Types', 'icon': 'star'},
                        {'title': 'Olympic Attachments', 'description': 'Compatible with Olympic Weight Plates', 'icon': 'weight'}
                    ],
                    'specifications': [
                        {'label': 'Weight Stack', 'value': '2 x 160 KG Steel'},
                        {'label': 'Cable System', 'value': '7x19 Strand Aircraft Cable'},
                        {'label': 'Stations', 'value': '8 Exercise Stations'},
                        {'label': 'Max User Weight', 'value': '150 KG'},
                        {'label': 'Dimensions', 'value': '320 x 220 x 220 CM'},
                        {'label': 'Frame', 'value': '12 Gauge Steel'},
                        {'label': 'Finish', 'value': 'Electrostatic Powder Coat'},
                        {'label': 'Warranty', 'value': 'Lifetime Frame / 2 Years Parts'},
                    ],
                    'benefits': [
                        {'title': 'Complete Workout Solution', 'description': 'Multiple exercise stations for full-body training'},
                        {'title': 'Commercial Quality', 'description': 'Heavy-duty construction built for gym environments'},
                        {'title': 'Space Efficient', 'description': 'Compact footprint for commercial and home gyms'},
                        {'title': 'Versatile Training', 'description': 'Suitable for strength, power, and functional training'}
                    ],
                    'perfect_for': [
                        {'label': 'Strength Training', 'icon': 'dumbbell'},
                        {'label': 'Muscle Building', 'icon': 'power'},
                        {'label': 'Functional Fitness', 'icon': 'target'},
                        {'label': 'Commercial Gyms', 'icon': 'shield'}
                    ],
                    'additional_stats': [
                        {'label': 'Rating', 'value': '4.7/5', 'icon': 'star'},
                        {'label': 'Weight Stack', 'value': '160 KG', 'icon': 'weight'},
                        {'label': 'Stations', 'value': '8', 'icon': 'dumbbell'}
                    ]
                },
                {
                    'name': 'Olympic Weight Bench',
                    'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'price': 24999,
                    'mrp': 35000,
                    'key_features': [
                        {'title': 'Olympic Compatibility', 'description': 'Fits 50mm Olympic Bars & Plates', 'icon': 'weight'},
                        {'title': 'Adjustable Positions', 'description': '7 Backrest Positions + Leg Extension', 'icon': 'star'},
                        {'title': 'Heavy Duty Frame', 'description': '3" x 3" Steel Tubing Construction', 'icon': 'power'},
                        {'title': 'Safety Features', 'description': 'Spotter Arms & Safety Locks', 'icon': 'shield'}
                    ],
                    'specifications': [
                        {'label': 'Frame Construction', 'value': '3" x 3" Steel Tubing'},
                        {'label': 'Weight Capacity', 'value': '400 KG'},
                        {'label': 'Backrest Positions', 'value': '7 Adjustable Positions'},
                        {'label': 'Dimensions', 'value': '165 x 70 x 50 CM'},
                        {'label': 'Barbell Holder', 'value': 'Built-in Olympic Holders'},
                        {'label': 'Upholstery', 'value': 'High Density Foam'},
                        {'label': 'Finish', 'value': 'Scratch Resistant Powder Coat'},
                        {'label': 'Warranty', 'value': '5 Years Frame / 1 Year Parts'},
                    ],
                    'benefits': [
                        {'title': 'Versatile Training', 'description': 'Perfect for bench press, incline press, and accessory work'},
                        {'title': 'Olympic Standard', 'description': 'Compatible with all Olympic weight plates and bars'},
                        {'title': 'Professional Quality', 'description': 'Commercial-grade construction for serious lifters'},
                        {'title': 'Safety First', 'description': 'Built-in safety features and stable design'}
                    ],
                    'perfect_for': [
                        {'label': 'Bench Press', 'icon': 'dumbbell'},
                        {'label': 'Chest Development', 'icon': 'power'},
                        {'label': 'Powerlifting', 'icon': 'weight'},
                        {'label': 'Home Gym', 'icon': 'shield'}
                    ],
                    'additional_stats': [
                        {'label': 'Rating', 'value': '4.4/5', 'icon': 'star'},
                        {'label': 'Weight Capacity', 'value': '400 KG', 'icon': 'weight'},
                        {'label': 'Positions', 'value': '7', 'icon': 'star'}
                    ]
                }
            ],
            'core': [
                {
                    'name': 'Abdominal Crunch Machine',
                    'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'price': 45999,
                    'mrp': 60000,
                    'key_features': [
                        {'title': 'Isolated Movement', 'description': 'Targets Abdominal Muscles Specifically', 'icon': 'target'},
                        {'title': 'Adjustable Resistance', 'description': 'Weight Stack from 10-100 KG', 'icon': 'weight'},
                        {'title': 'Ergonomic Design', 'description': 'Padded Seat & Back Support', 'icon': 'star'},
                        {'title': 'Smooth Operation', 'description': 'Precision Bearings & Cable System', 'icon': 'bolt'}
                    ],
                    'specifications': [
                        {'label': 'Weight Stack', 'value': '100 KG Steel'},
                        {'label': 'Resistance Range', 'value': '10 - 100 KG'},
                        {'label': 'Movement', 'value': 'Isolated Abdominal Crunch'},
                        {'label': 'Dimensions', 'value': '120 x 80 x 150 CM'},
                        {'label': 'Frame', 'value': '2" x 3" Steel Tubing'},
                        {'label': 'Upholstery', 'value': 'Medical Grade Vinyl'},
                        {'label': 'Finish', 'value': 'Electrostatic Powder Coat'},
                        {'label': 'Warranty', 'value': '2 Years Commercial'},
                    ],
                    'benefits': [
                        {'title': 'Targeted Training', 'description': 'Isolates abdominal muscles for maximum effectiveness'},
                        {'title': 'Progressive Overload', 'description': 'Adjustable resistance allows for progression over time'},
                        {'title': 'Joint Friendly', 'description': 'Controlled movement reduces risk of injury'},
                        {'title': 'Versatile Use', 'description': 'Suitable for all fitness levels and training goals'}
                    ],
                    'perfect_for': [
                        {'label': 'Core Strength', 'icon': 'target'},
                        {'label': 'Ab Definition', 'icon': 'dumbbell'},
                        {'label': 'Stability Training', 'icon': 'shield'},
                        {'label': 'Rehabilitation', 'icon': 'heart'}
                    ],
                    'additional_stats': [
                        {'label': 'Rating', 'value': '4.2/5', 'icon': 'star'},
                        {'label': 'Max Resistance', 'value': '100 KG', 'icon': 'weight'},
                        {'label': 'Movement Type', 'value': 'Isolated', 'icon': 'target'}
                    ]
                },
                {
                    'name': 'Roman Chair Hyperextension',
                    'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'price': 18999,
                    'mrp': 25000,
                    'key_features': [
                        {'title': '45° Angle Design', 'description': 'Optimal Position for Back Extension', 'icon': 'star'},
                        {'title': 'Foam Roller Padding', 'description': 'Comfortable Support for Extended Workouts', 'icon': 'heart'},
                        {'title': 'Sturdy Construction', 'description': 'Heavy Duty Steel Frame', 'icon': 'power'},
                        {'title': 'Versatile Use', 'description': 'Back Extensions & Oblique Work', 'icon': 'dumbbell'}
                    ],
                    'specifications': [
                        {'label': 'Frame Material', 'value': '2" Steel Tubing'},
                        {'label': 'Angle', 'value': '45° Fixed Position'},
                        {'label': 'Padding', 'value': 'High Density Foam Roller'},
                        {'label': 'Dimensions', 'value': '90 x 70 x 90 CM'},
                        {'label': 'Weight Capacity', 'value': '150 KG'},
                        {'label': 'Assembly', 'value': 'Bolt Together Design'},
                        {'label': 'Finish', 'value': 'Powder Coat Paint'},
                        {'label': 'Warranty', 'value': '1 Year Commercial'},
                    ],
                    'benefits': [
                        {'title': 'Back Health', 'description': 'Strengthens posterior chain and improves posture'},
                        {'title': 'Injury Prevention', 'description': 'Develops core stability and spinal support'},
                        {'title': 'Functional Strength', 'description': 'Improves overall athletic performance'},
                        {'title': 'Rehabilitation', 'description': 'Perfect for back rehabilitation programs'}
                    ],
                    'perfect_for': [
                        {'label': 'Back Strength', 'icon': 'power'},
                        {'label': 'Posture Improvement', 'icon': 'star'},
                        {'label': 'Core Stability', 'icon': 'shield'},
                        {'label': 'Rehab Training', 'icon': 'heart'}
                    ],
                    'additional_stats': [
                        {'label': 'Rating', 'value': '4.1/5', 'icon': 'star'},
                        {'label': 'Weight Capacity', 'value': '150 KG', 'icon': 'weight'},
                        {'label': 'Angle', 'value': '45°', 'icon': 'star'}
                    ]
                }
            ]
        }

        # Create products for each category
        for category_slug, products in equipment_data.items():
            category = categories[category_slug]

            for product_data in products:
                product, created = Product.objects.get_or_create(
                    slug=slugify(product_data['name']),
                    defaults={
                        'category': category,
                        'name': product_data['name'],
                        'description': f'Premium {product_data["name"]} designed for peak performance and durability.',
                        'image': f'products/{slugify(product_data["name"])}.jpg',
                        'mrp': product_data['mrp'],
                        'price': product_data['price'],
                        'discount_percent': round((1 - product_data['price']/product_data['mrp']) * 100),
                        'rating': float(product_data['additional_stats'][0]['value'].split('/')[0]),
                        'is_active': True,
                        'video_url': product_data['video_url'],
                        'key_features': product_data['key_features'],
                        'specifications': product_data['specifications'],
                        'benefits': product_data['benefits'],
                        'perfect_for': product_data['perfect_for'],
                        'additional_stats': product_data['additional_stats']
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f'✅ Created product: {product.name}'))

                    # Add gallery images
                    gallery_captions = [
                        'Front View',
                        'Side View',
                        'Detail View',
                        'In Use'
                    ]

                    for i, caption in enumerate(gallery_captions):
                        ProductImage.objects.create(
                            product=product,
                            image=f'products/gallery/{slugify(product.name)}-image-{i+1}.jpg',
                            caption=caption,
                            display_order=i
                        )
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  Product already exists: {product.name}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Sample equipment data populated successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Created {len(categories)} categories with multiple products each'))
        self.stdout.write(self.style.WARNING('Note: Remember to add actual images to the media folder'))

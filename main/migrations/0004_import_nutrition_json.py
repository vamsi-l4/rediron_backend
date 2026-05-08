from django.db import migrations


def load_nutrition(apps, schema_editor):
    import os
    import json
    from django.utils.dateparse import parse_datetime
    from django.utils import timezone

    NutritionArticle = apps.get_model("main", "NutritionArticle")

    # locate fixture relative to this migrations file
    migrations_dir = os.path.dirname(__file__)
    fixture_path = os.path.normpath(os.path.join(migrations_dir, "..", "fixtures", "nutrition_data_final_researched.json"))

    if not os.path.exists(fixture_path):
        # try alternative location (project root)
        fixture_path = os.path.normpath(os.path.join(os.path.dirname(migrations_dir), "fixtures", "nutrition_data_final_researched.json"))

    if not os.path.exists(fixture_path):
        # nothing to import
        return

    def parse_published_at(value):
        if not value:
            return timezone.now()
        if isinstance(value, dict):
            date = value.get("Date")
            time = value.get("Time")
            if date and time:
                dt = parse_datetime(f"{date}T{time}")
                if dt:
                    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        if isinstance(value, str):
            dt = parse_datetime(value)
            if dt:
                return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        return timezone.now()

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles") or []

    for item in articles:
        title = (item.get("Title") or item.get("title") or "").strip()
        if not title:
            continue
        slug = (item.get("Slug") or item.get("slug") or "").strip()
        excerpt = item.get("Excerpt") or item.get("excerpt") or ""
        content = item.get("Content") or item.get("content") or ""
        author = item.get("Author") or item.get("author") or "RedIron Team"
        category = item.get("Category") or item.get("category") or "Nutrition"
        tags = item.get("Tags") or item.get("tags") or ""
        feat_img_url = item.get("Featured image url") or item.get("featured_image_url") or ""
        feat_img_path = item.get("Featured image") or item.get("featured_image") or ""
        if not feat_img_url and isinstance(feat_img_path, str) and feat_img_path.strip():
            feat_img_url = feat_img_path.strip()

        published_at_val = item.get("LastEdited") or item.get("Last Edited") or item.get("Published at") or None
        published_at = parse_published_at(published_at_val)

        is_published = item.get("Is published")
        if is_published is None:
            is_published = item.get("is_published", True)

        featured = item.get("Featured")
        if featured is None:
            featured = item.get("featured", False)

        references = item.get("References") or item.get("references") or None

        # normalize category
        if category not in ["Nutrition", "Supplements", "Recipes"]:
            category = "Nutrition"

        # try to find existing by slug then title+published_at
        existing = None
        if slug:
            existing = NutritionArticle.objects.filter(slug=slug).first()
        if not existing:
            existing = NutritionArticle.objects.filter(title=title, published_at=published_at).first()

        if existing:
            # update
            existing.title = title
            if slug:
                existing.slug = slug
            existing.author = author
            existing.excerpt = excerpt
            existing.content = content
            if feat_img_url:
                existing.featured_image_url = feat_img_url
            existing.category = category
            existing.tags = tags
            existing.published_at = published_at
            existing.is_published = bool(is_published)
            existing.featured = bool(featured)
            existing.references = references
            existing.save()
        else:
            NutritionArticle.objects.create(
                title=title,
                slug=slug or "",
                author=author,
                excerpt=excerpt,
                content=content,
                featured_image_url=feat_img_url,
                category=category,
                tags=tags,
                published_at=published_at,
                is_published=bool(is_published),
                featured=bool(featured),
                references=references,
            )


def noop_reverse(apps, schema_editor):
    # keep migration reversible but don't delete articles automatically
    return


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_alter_nutritionarticle_content"),
    ]

    operations = [
        migrations.RunPython(load_nutrition, reverse_code=noop_reverse),
    ]

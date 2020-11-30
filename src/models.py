from tortoise.models import Model
from tortoise import fields


class Star(Model):
    id = fields.IntField(pk=True)
    recipient = fields.ForeignKeyField(model_name='models.Recipient', related_name='star')
    presenter_id = fields.IntField()
    reason = fields.CharField(max_length=512)
    timestamp = fields.data.DatetimeField(auto_now_add=True)

    async def save(self, *args, **kwargs):
        await super(Star, self).save(*args, **kwargs)
        await self.recipient.count_stars()

    async def delete(self, *args, **kwargs):
        tmp_object = await self.recipient
        await super(Star, self).delete(*args, **kwargs)
        await tmp_object.count_stars()


class Recipient(Model):
    id = fields.IntField(pk=True)
    star_count = fields.IntField(default=0)

    star: fields.ReverseRelation[Star]

    def mention(self):
        return f"<@{self.id}>"

    async def count_stars(self):
        await self.fetch_related('star')
        self.star_count = len(self.star)
        await self.save()
        return self.star_count

from django.db import models
from django.contrib.postgres.fields import ArrayField


class CustomModel(models.Model):

    class Meta:
        abstract = True
        managed = True

class Department(CustomModel):
    id = models.BigAutoField(primary_key=True)
    room_number = models.IntegerField()
    internal_phone = models.IntegerField()
    employee_count = models.IntegerField()
    employee_phones = ArrayField(
        base_field=models.IntegerField(),
        default=list,
        blank=True,
        null=True
    )

    class Meta(CustomModel.Meta):
        db_table = 'Department'
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'

    def __str__(self):
        return f"Отдел {self.room_number} (тел: {self.internal_phone})"


class Computer(CustomModel):
    id = models.BigAutoField(primary_key=True)
    serial_number = models.IntegerField()
    model = models.CharField(max_length=100)
    os = models.CharField(max_length=100)
    inventory_number = models.IntegerField()
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='computers'
    )

    class Meta(CustomModel.Meta):
        db_table = 'Computer'
        verbose_name = 'Компьютер'
        verbose_name_plural = 'Компьютеры'

    def __str__(self):
        return f"{self.model} (SN: {self.serial_number})"


class User(CustomModel):
    id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=50)
    email = models.CharField(max_length=100)
    position_id = models.BigIntegerField()
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    computers = models.ManyToManyField(
        Computer,
        through='UserComputer',
        related_name='users'
    )

    class Meta(CustomModel.Meta):
        db_table = 'User'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.full_name


class UserComputer(CustomModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='User_id'
    )
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        db_column='Computer_id'
    )

    class Meta(CustomModel.Meta):
        db_table = 'User_Computer'
        unique_together = [['user', 'computer']]
        verbose_name = 'Пользователь-Компьютер'
        verbose_name_plural = 'Связи Пользователь-Компьютер'


class Software(CustomModel):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    version = models.CharField(max_length=100)
    license = models.CharField(max_length=200)
    vendor = models.CharField(max_length=200)
    computers = models.ManyToManyField(
        Computer,
        through='SoftwareComputer',
        related_name='software'
    )

    class Meta(CustomModel.Meta):
        db_table = 'Software'
        verbose_name = 'Программное обеспечение'
        verbose_name_plural = 'Программное обеспечение'

    def __str__(self):
        return f"{self.name} {self.version}"


class SoftwareComputer(CustomModel):
    software = models.ForeignKey(
        Software,
        on_delete=models.CASCADE,
        db_column='Software_id'
    )
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        db_column='Computer_id'
    )

    class Meta(CustomModel.Meta):
        db_table = 'Software_Computer'
        unique_together = [['software', 'computer']]
        verbose_name = 'ПО-Компьютер'
        verbose_name_plural = 'Связи ПО-Компьютер'


class Equipment(CustomModel):
    id = models.BigAutoField(primary_key=True)
    bandwidth = models.IntegerField()
    setup_date = models.DateField()
    port_count = models.IntegerField()
    type = models.CharField(max_length=50)

    class Meta(CustomModel.Meta):
        db_table = 'Equipment'
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудование'

    def __str__(self):
        return f"{self.type} (портов: {self.port_count})"


class Network(CustomModel):
    id = models.BigAutoField(primary_key=True)
    subnet_mask = models.GenericIPAddressField()
    vlan = models.SmallIntegerField()
    ip_range = models.CharField(max_length=100)
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='networks'
    )
    computers = models.ManyToManyField(
        Computer,
        through='NetworkComputer',
        related_name='networks'
    )

    class Meta(CustomModel.Meta):
        db_table = 'Network'
        verbose_name = 'Сеть'
        verbose_name_plural = 'Сети'

    def __str__(self):
        return f"VLAN {self.vlan} ({self.ip_range})"


class NetworkComputer(CustomModel):
    id = models.BigAutoField(primary_key=True)
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        db_column='Network_id'
    )
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        db_column='Computer_id'
    )
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=17)
    speed = models.IntegerField()

    class Meta(CustomModel.Meta):
        db_table = 'Network_Computer'
        unique_together = [['network', 'computer']]
        verbose_name = 'Сеть-Компьютер'
        verbose_name_plural = 'Связи Сеть-Компьютер'


class Server(CustomModel):
    id = models.BigAutoField(primary_key=True)
    port = models.IntegerField()
    hostname = models.CharField(max_length=255)
    connection_date = models.DateField()
    location = models.CharField(max_length=255)
    networks = models.ManyToManyField(
        Network,
        through='ServerNetwork',
        related_name='servers'
    )

    class Meta(CustomModel.Meta):
        db_table = 'Server'
        verbose_name = 'Сервер'
        verbose_name_plural = 'Серверы'

    def __str__(self):
        return self.hostname


class ServerNetwork(CustomModel):
    server = models.ForeignKey(
        Server,
        on_delete=models.CASCADE,
        db_column='Server_id'
    )
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        db_column='Network_id'
    )

    class Meta(CustomModel.Meta):
        db_table = 'Server_Network'
        unique_together = [['server', 'network']]
        verbose_name = 'Сервер-Сеть'
        verbose_name_plural = 'Связи Сервер-Сеть'


class HostComputer(CustomModel):
    id = models.BigAutoField(primary_key=True)
    hostname = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=17)
    department = models.OneToOneField(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        unique=True
    )

    class Meta(CustomModel.Meta):
        db_table = 'Host_Computer'
        verbose_name = 'Хост-компьютер'
        verbose_name_plural = 'Хост-компьютеры'

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"
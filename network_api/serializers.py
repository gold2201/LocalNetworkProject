from rest_framework import serializers
from .models import Department, Computer, User, Software, Network, NetworkComputer, Equipment


class DepartmentSerializer(serializers.ModelSerializer):
    computers_count = serializers.SerializerMethodField()
    avg_computers_per_employee = serializers.SerializerMethodField()
    is_large_department = serializers.SerializerMethodField()

    host_computer_ip = serializers.CharField(
        source='host_computer.ip_address',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Department
        fields = [
            'id', 'room_number', 'internal_phone',
            'employee_count', 'employee_phones',
            'computers_count', 'avg_computers_per_employee',
            'is_large_department', 'host_computer_ip'
        ]
        read_only_fields = ['id']

    def get_computers_count(self, obj):
        return obj.computers.count()

    def get_avg_computers_per_employee(self, obj):
        if obj.employee_count > 0:
            return round(obj.computers.count() / obj.employee_count, 2)
        return 0

    def get_is_large_department(self, obj):
        return obj.employee_count > 10

    def validate_room_number(self, value):
        if value < 1 or value > 99:
            raise serializers.ValidationError(
                "Номер комнаты должен быть от 1 до 9"
            )
        return value

    def validate_employee_count(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "В отделе должен быть хотя бы 1 сотрудник"
            )
        if value > 20:
            raise serializers.ValidationError(
                "Слишком много сотрудников для одного отдела"
            )
        return value

    def validate(self, attrs):
        room_number = attrs.get('room_number')
        employee_count = attrs.get('employee_count', 0)

        if employee_count > 10 and room_number < 50:
            raise serializers.ValidationError({
                'room_number': 'Крупные отделы размещаются в комнатах 50+'
            })

        return attrs

    def create(self, validated_data):
        print(f"Создается отдел в комнате {validated_data['room_number']}")

        if 'employee_phones' not in validated_data:
            validated_data['employee_phones'] = []

        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_room = instance.room_number
        old_employee_count = instance.employee_count

        instance = super().update(instance, validated_data)

        if old_room != instance.room_number:
            print(f"Отдел {instance.id} перемещен из {old_room} в {instance.room_number}")

        return instance


class ComputerSerializer(serializers.ModelSerializer):

    department_info = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    software_list = serializers.SerializerMethodField()
    network_speed = serializers.SerializerMethodField()

    class Meta:
        model = Computer
        fields = [
            'id', 'serial_number', 'model', 'os',
            'inventory_number', 'department', 'department_info',
            'users_count', 'software_list', 'network_speed'
        ]

    def get_department_info(self, obj):
        if obj.department:
            return f"Комната {obj.department.room_number} (тел: {obj.department.internal_phone})"
        return "Не назначен"

    def get_users_count(self, obj):
        return obj.users.count()

    def get_software_list(self, obj):
        return list(obj.software.values_list('name', flat=True))

    def get_network_speed(self, obj):
        network_conn = obj.network_computer_set.first()
        return network_conn.speed if network_conn else 0

    def validate_serial_number(self, value):
        instance = self.instance
        if instance:
            exists = Computer.objects.filter(
                serial_number=value
            ).exclude(id=instance.id).exists()
        else:
            exists = Computer.objects.filter(serial_number=value).exists()

        if exists:
            raise serializers.ValidationError("Компьютер с таким серийным номером уже существует")
        return value

    def create(self, validated_data):
        computer = super().create(validated_data)

        from .models import NetworkComputer, Network
        default_network = Network.objects.first()
        if default_network:
            NetworkComputer.objects.create(
                network=default_network,
                computer=computer,
                ip_address='192.168.1.100',
                mac_address='00:00:00:00:00:00',
                speed=100
            )

        return computer


class UserSerializer(serializers.ModelSerializer):

    department_room = serializers.CharField(
        source='department.room_number',
        read_only=True
    )
    computers_info = serializers.SerializerMethodField()
    can_manage_network = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'email',
            'position_id', 'department', 'department_room',
            'computers_info', 'can_manage_network'
        ]

    def get_computers_info(self, obj):
        computers = obj.computers.all()
        return [
            {
                'id': comp.id,
                'model': comp.model,
                'os': comp.os
            } for comp in computers
        ]

    def get_can_manage_network(self, obj):
        return obj.position_id in [1, 2]

    def validate_email(self, value):
        if not value.endswith(('@company.com', '@corp.com')):
            raise serializers.ValidationError(
                "Используйте корпоративную почту (@company.com или @corp.com)"
            )
        return value

    def validate(self, attrs):
        position_id = attrs.get('position_id')
        department = attrs.get('department')

        if position_id in [1, 2] and not department:
            raise serializers.ValidationError({
                'department': 'Руководители должны быть привязаны к отделу'
            })

        return attrs


class SoftwareSerializer(serializers.ModelSerializer):
    installed_count = serializers.SerializerMethodField()
    popular_os = serializers.SerializerMethodField()
    needs_license_renewal = serializers.SerializerMethodField()

    class Meta:
        model = Software
        fields = [
            'id', 'name', 'version', 'license', 'vendor',
            'installed_count', 'popular_os', 'needs_license_renewal'
        ]

    def get_installed_count(self, obj):
        return obj.computers.count()

    def get_popular_os(self, obj):
        os_list = obj.computers.values_list('os', flat=True).distinct()
        return list(os_list)

    def get_needs_license_renewal(self, obj):
        return 'trial' in obj.license.lower() or 'expired' in obj.license.lower()

    def create(self, validated_data):
        if 'version' not in validated_data:
            validated_data['version'] = '1.0.0'

        software = super().create(validated_data)
        print(f"Добавлено ПО: {software.name} {software.version}")

        return software

class NetworkComputerSerializer(serializers.ModelSerializer):
    computer_model = serializers.CharField(
        source='computer.model',
        read_only=True
    )

    class Meta:
        model = NetworkComputer
        fields = ['computer_model']

class NetworkSerializer(serializers.ModelSerializer):
    port_count_eq = serializers.CharField(
        source='equipment.port_count',
        read_only=True
    )

    network_computers = NetworkComputerSerializer(
        source='networkcomputer_set',
        many=True,
        read_only=True
    )

    class Meta:
        model = Network
        fields = [
            'id', 'subnet_mask', 'vlan',
            'ip_range', 'port_count_eq', 'network_computers'
        ]

class EquipmentSerializer(serializers.ModelSerializer):

    type_of_bandwidth = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['id', 'type', 'bandwidth', 'port_count', 'setup_date', 'type_of_bandwidth']

    def get_type_of_bandwidth(self, obj):
        if obj.bandwidth == 100:
            return 'Базовый интернет'
        elif obj.bandwidth == 1000:
            return 'Онлайн-игры'
        else:
            return 'Видеозвонки'
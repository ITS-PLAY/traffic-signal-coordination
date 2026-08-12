
# 车辆类型类，定义车辆的换道行为
class VehType:
    laneChangeDuration = "2.0"
    overtakeRight = "true"
    lcStrategic = "2.0"
    lcCooperative = "0.7" # 减少相互等待
    lcAssertive = "1.8" # 果断换道
    lcSpeedGain = "1.0"
    lcKeepRight = "0.5" #左转车辆优先左侧
    def __init__(self, id='car'):
        self.id = id

    def to_xml(self):
        xml_lines = ['<additional>']
        veh_type = (f'<vType id="{self.id}" laneChangeDuration="{self.laneChangeDuration}"'
                    f' overtakeRight="{self.overtakeRight}" lcStrategic="{self.lcStrategic}"'
                    f' lcCooperative="{self.lcCooperative}" lcAssertive="{self.lcAssertive}"'
                    f' lcSpeedGain="{self.lcSpeedGain}" lcKeepRight="{self.lcKeepRight}"/>')
        xml_lines.append(veh_type)
        xml_lines.append('</additional>')
        return '\n'.join(xml_lines)

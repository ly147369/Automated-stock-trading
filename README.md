
股票自动化交易

## 使用说明
* 开发环境是win10 64bit, python3 64bit、pywin32、tushare。当然32bit python3也可以的
* 软件共有3个文件，`pyautotrade.pyw`主程序，`stockInfo.dat`存盘文件，`winguiauto.py`是封装的winapi函数
* 交易软件启动后，直接点击左边树形列表`对买对卖`，然后启动本程序，不要再切换到其它界面，始终在`对买对卖`界面上
* 不写时间条件单，默认时间为凌晨1点。时间条件满足后才检查价格条件，如果只想要时间条件单而忽略价格条件单，可以写个始终满足条件的价格。
* 股票数量为100的倍数, 如果输入150股将作为100股。默认为0股，也就说，股票数量由交易软件自动填写，当然需提前在交易软件里设定好，在`系统设置-仓位策略`里选择固定数量,
* 时间为24小时制，形式为 `时：分：秒`， 每项都必须写， 后面的写法是错误的： `13：30`
* 交易软件的委托价格由交易软件自动填写，在`系统设置-自动策略`， 启用`启用自动跟盘`， 自己决定选哪个价格




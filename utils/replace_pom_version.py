import sys
import os
import xml.etree.ElementTree as ET


class CommentedTreeBuilder(ET.TreeBuilder):
    def comment(self, data):
        self.start(ET.Comment, {})
        self.data(data)
        self.end(ET.Comment)


# 循环当前项目下的所有文件，处理所有的POM文件
def deal_pom_file(path, project_v, iterate_v, project_tags):
    # 循环扫描路径下所有文件
    all_file = os.walk(path)
    for file_path, dir_names, file_names in all_file:
        for file_name in file_names:
            if "pom.xml" == file_name:
                # 开始处理POM文件
                deal_pom_xml(os.path.join(file_path, file_name), project_v, iterate_v, project_tags)


# 处理单个POM文件
def deal_pom_xml(xml_file, project_v, iterate_v, project_tags):
    print("开始处理pom文件：" + xml_file)
    ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
    parser = ET.XMLParser(target=CommentedTreeBuilder())
    tree = ET.parse(xml_file, parser)
    root = tree.getroot()

    for child in root:
        # 处理 根节点下的version
        if str(child.tag).endswith('version'):
            if '$' not in child.text:
                child.text = project_v

        # 处理 profiles 下的版本号
        if str(child.tag).endswith('profiles'):
            for sub in child:
                iterate_flag = False
                for sub_child in sub:
                    if str(sub_child.tag).endswith('id') and sub_child.text == 'feature':
                        iterate_flag = True
                    if str(sub_child.tag).endswith('properties'):
                        for sub_sub_child in sub_child:
                            if str(sub_sub_child.tag).endswith(project_tags):
                                if iterate_flag:
                                    sub_sub_child.text = iterate_v
                                else:
                                    sub_sub_child.text = project_v

        # 处理 parent 下的version
        if str(child.tag).endswith('parent'):
            for sub in child:
                if str(sub.tag).endswith('version'):
                    if '$' not in sub.text:
                        sub.text = project_v
                        break
    # 处理根节点的version
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)


# 拿到所有需要修改的标签
def trance_project_map(project_arr):
    base_map = {
        'bus-frp-aat':['frp.aat.version', 'aat.client.version'],
        'bus-frp-rdf':['frp.rdf.version', 'rdf.client.version'],
        'bus-frp-fmi':[],
        'bus-frp-rdf-mirror':['frp.rdf.mirror'],
        'bus-frp-auth':['frp.auth.version', 'auth.client.version'],
        'us-frp-fesb':[],
        'bus-frp-fpr':['frp.fpr.version'],
        'bus-frp-bfs':['bfs.client.version'],
        'bus-frp-fpm':['fpm.client.version'],
        'bus-frp-job':[],
        'bus-frp-report':['frp.report.version'],
        'bus-frp-message':['frp.message.version'],
        'bus-frp-file':['bus.frp.file.version'],
        'fofund-i18n':[],
        'fofund-research':[],
        'fofund-research-wind':[]
    }
    project_tag_list = ['current.project.version']

    for project_name in project_arr:
        if base_map[project_name]:
            project_tag_list.extend(base_map[project_name])

    return tuple(project_tag_list)


if __name__ == '__main__':
    # 待扫描根路径
    if len(sys.argv) < 5:
        print("请检查脚本入参格式后重新输入:")
        print("python replace_pom_version.py path yyyyMMdd version project_a,project_b")
        print("例如：python replace_pom_version.py D:\workspace 20221027 334 bus-frp-aat,bus-frp-rdf")
        quit()

    root_path = sys.argv[1]
    # 待更改版本号 20221027
    input_version = sys.argv[2]
    project_version = '1.0.' + input_version + '-SNAPSHOT'
    # 迭代号
    input_iterate = sys.argv[3]
    iterate_version = '1.0.' + input_version + '.' + input_iterate + '-SNAPSHOT'
    # project名称集合 bus_frp_aat, buf_frp_rdf
    input_project_arr = sys.argv[4].split(',')
    project_tag = trance_project_map(input_project_arr)

    print("开始扫描文件路径：" + root_path + "下的文件")
    list_dir = os.listdir(root_path)
    # 循环处理扫描路径下的文件
    for file in list_dir:
        # 跳过非指定项目
        if file not in input_project_arr:
            continue
        project_path = os.path.join(root_path, file)
        deal_pom_file(project_path, project_version, iterate_version, project_tag)
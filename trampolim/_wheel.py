# SPDX-License-Identifier: MIT

import os.path
import textwrap

import wheel.wheelfile

import trampolim._build


class WheelBuilder():
    def __init__(self, project: trampolim._build.Project) -> None:
        self._project = project

    @property
    def name(self) -> str:
        return '{distribution}-{version}-{python_tag}-{abi_tag}-{platform_tag}'.format(
            distribution=self._project.name.replace('-', '_'),
            version=self._project.version,
            python_tag=self._project.python_tag,
            abi_tag=self._project.abi_tag,
            platform_tag=self._project.platform_tag,
        )

    @property
    def file(self) -> str:
        return f'{self.name}.whl'

    def build(self, path: trampolim._build.Path) -> None:
        self._project.run_tasks()
        with wheel.wheelfile.WheelFile(os.path.join(path, self.file), 'w') as whl:
            with self._project.cd_binary_source():
                # add source
                for destination, source_path in self._project.binary_source.items():
                    whl.write(source_path, arcname=destination.as_posix())

                # add metadata
                whl.writestr(f'{whl.dist_info_path}/METADATA', bytes(self._project._meta.as_rfc822()))
                whl.writestr(f'{whl.dist_info_path}/WHEEL', self.wheel)
                if self.entrypoints_txt:
                    whl.writestr(f'{whl.dist_info_path}/entrypoints.txt', self.entrypoints_txt)

    @property
    def wheel(self) -> bytes:
        '''dist-info WHEEL.'''
        return textwrap.dedent('''
            Wheel-Version: 1.0
            Generator: trampolim {version}
            Root-Is-Purelib: {is_purelib}
            Tag: {tags}
        ''').strip().format(
            version=trampolim.__version__,
            is_purelib='true' if self._project.abi_tag == 'none' else 'false',
            tags=f'{self._project.python_tag}-{self._project.abi_tag}-{self._project.platform_tag}',
        ).encode()

    @property
    def entrypoints_txt(self) -> bytes:
        '''dist-info entry-points.txt.'''
        data = self._project._meta.entrypoints.copy()
        data.update({
            'console_scripts': self._project._meta.scripts,
            'gui_scripts': self._project._meta.gui_scripts,
        })

        text = ''
        for entrypoint in data:
            if data[entrypoint]:
                text += f'[{entrypoint}]\n'
                for name, target in data[entrypoint].items():
                    text += f'{name} = {target}\n'
                text += '\n'

        return text.encode()

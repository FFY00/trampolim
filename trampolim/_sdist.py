# SPDX-License-Identifier: MIT

import contextlib
import gzip
import io
import os.path
import pathlib
import tarfile
import typing

from typing import IO

import trampolim._build


class SdistBuilder():
    '''Simple sdist builder.

    Will only include by default the files relevant for source code distribution
    and the required files to be able to build binary distributions.
    '''
    def __init__(self, project: trampolim._build.Project) -> None:
        self._project = project

    @property
    def name(self) -> str:
        return f'{self._project.name}-{self._project.version}'

    @property
    def file(self) -> str:
        return f'{self.name}.tar.gz'

    def build(self, path: trampolim._build.Path) -> None:
        # reproducibility
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        mtime = int(source_date_epoch) if source_date_epoch else None

        # open files
        file = typing.cast(
            IO[bytes],
            gzip.GzipFile(
                os.path.join(path, self.file),
                mode='wb',
                mtime=mtime,
            ),
        )
        tar = tarfile.TarFile(
            str(path),
            mode='w',
            fileobj=file,
            format=tarfile.PAX_FORMAT,  # changed in 3.8 to GNU
        )

        with contextlib.closing(file), tar:
            with self._project.cd_dist_source():
                # add source
                for path in self._project.distribution_source:
                    arcname = pathlib.Path(self.name) / path
                    tar.add(os.fspath(path), arcname.as_posix())

                # add version file
                info = tarfile.TarInfo(f'{self.name}/.trampolim/version')
                version_raw = str(self._project.version).encode()
                info.size = len(version_raw)
                with io.BytesIO(version_raw) as data:
                    tar.addfile(info, data)

                # add license
                license_ = self._project._meta.license
                if license_:
                    if license_.file:
                        tar.add(license_.file, f'{self.name}/{license_.file}')
                    elif license_.text:
                        license_raw = license_.text.encode()
                        info = tarfile.TarInfo(f'{self.name}/LICENSE')
                        info.size = len(license_raw)
                        with io.BytesIO(license_raw) as data:
                            tar.addfile(info, data)

                # add readme
                readme = self._project._meta.readme
                if readme:
                    tar.add(readme.file, f'{self.name}/{readme.file}')

            # PKG-INFO
            pkginfo = bytes(self._project._meta.as_rfc822())
            info = tarfile.TarInfo(f'{self.name}/PKG-INFO')
            info.size = len(pkginfo)
            with io.BytesIO(pkginfo) as data:
                tar.addfile(info, data)

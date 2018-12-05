import os
import numpy as np
from scipy.interpolate import Rbf

from lsst.ts.wep.cwfs.Tool import ZernikeFit, ZernikeEval


class MirrorSim(object):

    def __init__(self, innerRinM, outerRinM, mirrorDataDir=""):
        """Initiate the mirror simulator class.

        Parameters
        ----------
        innerRinM : float
            Mirror inner radius in m.
        outerRinM : float
            Mirror outer radius in m.
        mirrorDataDir : str, optional
            Mirror data directory. (the default is "".)
        """

        self.RiInM = innerRinM
        self.RinM = outerRinM
        self.mirrorDataDir = mirrorDataDir

        self._surf = np.array([])

    def getInnerRinM(self):
        """Get the inner radius of mirror in meter.

        Returns
        -------
        float or list
            Inner radius of mirror in meter.
        """

        return self.RiInM

    def getOuterRinM(self):
        """Get the outer radius of mirror in meter.

        Returns
        -------
        float or list
            Outer radius of mirror in meter.
        """

        return self.RinM

    def setMirrorDataDir(self, mirrorDataDir):
        """Set the directory of mirror data.

        Parameters
        ----------
        mirrorDataDir : str
            Directory to mirror data.
        """

        self.mirrorDataDir = mirrorDataDir

    def getMirrorData(self, dataFileName, skiprows=0):
        """Get the mirror data.

        Parameters
        ----------
        dataFileName : str
            Data file name.
        skiprows : int, optional
            Skip the first 'skiprows' lines (the default is 0.)

        Returns
        -------
        numpy.ndarray
            Mirror data.
        """

        filePath = os.path.join(self.mirrorDataDir, dataFileName)
        data = np.loadtxt(filePath, skiprows=skiprows)

        return data

    def setSurfAlongZ(self, surfAlongZinUm):
        """Set the mirror surface along the z direction in um.

        Parameters
        ----------
        surfAlongZinUm : numpy.ndarray
            Mirror surface along the z direction in um.
        """

        self._surf = np.array(surfAlongZinUm, dtype=float)

    def getSurfAlongZ(self):
        """Get the mirror surface along the z direction in um.

        Returns
        -------
        numpy.ndarray
            Mirror surface along the z direction in um.
        """

        return self._surf

    def getLUTforce(self, zangleInDeg, LUTfileName):
        """Get the actuator force of mirror based on LUT.

        LUT: Look-up table.

        Parameters
        ----------
        zangleInDeg : float
            Zenith angle in degree.
        LUTfileName : str
            LUT file name.

        Returns
        -------
        numpy.ndarray
            Actuator forces in specific zenith angle.

        Raises
        ------
        ValueError
            The degee order in LUT is incorrect.
        """

        # Read the LUT file
        lut = self.getMirrorData(LUTfileName)

        # Get the step. The values of LUT are listed in every step size.
        # The degree range is 0 - 90 degree.
        # The file in the simulation is every 1 degree. The formal one should
        # be every 5 degree.
        ruler = lut[0, :]
        stepList = np.diff(ruler)
        if np.any(stepList <= 0):
            raise ValueError("The degee order in LUT is incorrect.")

        # If the specific zenith angle is larger than the listed angle range,
        # use the biggest listed zenith angle data instead.
        if (zangleInDeg >= ruler.max()):
            lutForce = lut[1:, -1]

        # If the specific zenith angle is smaller than the listed angle range,
        # use the smallest listed zenith angle data instead.
        elif (zangleInDeg <= ruler.min()):
            lutForce = lut[1:, 0]

        # If the specific zenith angle is in the listed angle range,
        # do the linear fit to get the data.
        else:
            # Find the boundary indexes for the specific zenith angle
            p1 = np.where(ruler <= zangleInDeg)[0][-1]
            p2 = p1+1

            # Do the linear approximation
            w2 = (zangleInDeg-ruler[p1])/stepList[p1]
            w1 = 1-w2

            lutForce = w1*lut[1:, p1] + w2*lut[1:, p2]

        return lutForce

    def getActForce(self, actForceFileName):
        """Get the mirror actuator forces in N.

        Parameters
        ----------
        actForceFileName : str
            Actuator force file name.

        Returns
        ------
        numpy.ndarray
            Actuator forces in N.
        """

        forceInN = self.getMirrorData(actForceFileName)

        return forceInN

    def _gridSampInMnInZemax(self, zfInMm, xfInMm, yfInMm, innerRinMm,
                             outerRinMm, nx, ny, resFile=None):
        """Get the grid residue map used in Zemax.

        Parameters
        ----------
        zfInMm : numpy.ndarray
            Surface map in mm.
        xfInMm : numpy.ndarray
            X position in mm.
        yfInMm : numpy.ndarray
            Y position in mm.
        innerRinMm : float
            Inner radius in mm.
        outerRinMm : float
            Outer radius in mm.
        nx : int
            Number of pixel along x-axis of surface residue map. It is noted
            that the real pixel number is nx + 4.
        ny : int
            Number of pixel along y-axis of surface residue map. It is noted
            that the real pixel number is ny + 4.
        resFile : str, optional
            File path to write the surface residue map. (the default is None.)

        Returns
        -------
        str
            Grid residue map related data.
        """

        # Radial basis function approximation/interpolation of surface
        Ff = Rbf(xfInMm, yfInMm, zfInMm)

        # Number of grid points on x-, y-axis.
        # Alway extend 2 points on each side
        # Do not want to cover the edge? change 4->2 on both lines
        NUM_X_PIXELS = nx+4
        NUM_Y_PIXELS = ny+4

        # This is spatial extension factor, which is calculated by the slope
        # at edge
        extFx = (NUM_X_PIXELS-1) / (nx-1)
        extFy = (NUM_Y_PIXELS-1) / (ny-1)
        extFr = np.sqrt(extFx * extFy)

        # Delta x and y
        delx = outerRinMm*2*extFx / (NUM_X_PIXELS-1)
        dely = outerRinMm*2*extFy / (NUM_Y_PIXELS-1)

        # Minimum x and y
        minx = -0.5*(NUM_X_PIXELS-1)*delx
        miny = -0.5*(NUM_Y_PIXELS-1)*dely

        # Calculate the epsilon
        epsilon = 1e-4*min(delx, dely)

        # Write four numbers for the header line
        content = "%d %d %.9E %.9E\n" % (NUM_X_PIXELS, NUM_Y_PIXELS, delx,
                                         dely)

        #  Write the rows and columns
        for jj in range(1, NUM_X_PIXELS + 1):
            for ii in range(1, NUM_Y_PIXELS + 1):

                # x and y positions
                x = minx + (ii - 1) * delx
                y = miny + (jj - 1) * dely

                # Invert top to bottom, because Zemax reads (-x,-y) first
                y = -y

                # Calculate the radius
                r = np.sqrt(x**2 + y**2)

                # Set the value as zero when the radius is not between the
                # inner and outer radius.
                if (r < innerRinMm/extFr) or (r > outerRinMm*extFr):

                    z = 0
                    dx = 0
                    dy = 0
                    dxdy = 0

                # Get the value by the fitting
                else:

                    # Get the z
                    z = Ff(x, y)

                    # Compute the dx
                    tem1 = Ff((x+epsilon), y)
                    tem2 = Ff((x-epsilon), y)
                    dx = (tem1 - tem2)/(2.0*epsilon)

                    # Compute the dy
                    tem1 = Ff(x, (y+epsilon))
                    tem2 = Ff(x, (y-epsilon))
                    dy = (tem1 - tem2)/(2.0*epsilon)

                    # Compute the dxdy
                    tem1 = Ff((x+epsilon), (y+epsilon))
                    tem2 = Ff((x-epsilon), (y+epsilon))
                    tem3 = (tem1 - tem2)/(2.0*epsilon)

                    tem1 = Ff((x+epsilon), (y-epsilon))
                    tem2 = Ff((x-epsilon), (y-epsilon))
                    tem4 = (tem1 - tem2)/(2.0*epsilon)

                    dxdy = (tem3 - tem4)/(2.0*epsilon)

                content += "%.9E %.9E %.9E %.9E\n" % (z, dx, dy, dxdy)

        # Write the surface residue data into the file
        if (resFile is not None):
            outid = open(resFile, "w")
            outid.write(content)
            outid.close()

        return content

    def _getMirrorResInNormalizedCoor(self, surf, x, y, numTerms):
        """Get the residue of surface (mirror print along z-axis) after the
        fitting with Zk in the normalized x, y coordinate.

        Parameters
        ----------
        surf : numpy.ndarray
            Mirror surface.
        x : numpy.ndarray
            Normalized x coordinate.
        y : numpy.ndarray
            Normalized y coordinate.
        numTerms : int
            Number of Zernike terms to fit.

        Returns
        -------
        numpy.ndarray
            Surface residue after the fitting.
        numpy.ndarray
            Fitted Zernike polynomials.
        """

        # Get the surface change along the z-axis in the basis of Zk
        # It is noticed that the x and y coordinates are normalized for the
        # fitting.
        zc = ZernikeFit(surf, x, y, numTerms)

        # Residue of fitting
        res = surf - ZernikeEval(zc, x, y)

        return res, zc

    def getPrintthz(self, zAngleInRadian, preCompElevInRadian=0,
                    FEAfileName="", FEAzenFileName="",
                    FEAhorFileName="", gridFileName=""):
        """Get the mirror print in um along z direction in specific zenith
        angle.

        FEA: Finite element analysis.

        Parameters
        ----------
        zAngleInRadian : float
            Zenith angle in radian.
        preCompElevInRadian : float, optional
            Pre-compensation elevation angle in radian. (the default is 0.)
        FEAfileName : str, optional
            FEA model data file name. (the default is "".)
        FEAzenFileName : str, optional
            FEA model data file name in zenith angle. (the default is "".)
        FEAhorFileName : str, optional
            FEA model data file name in horizontal angle. (the default is "".)
        gridFileName : str, optional
            File name of bending mode data. (the default is "".)

        Returns
        ------
        numpy.ndarray
            Corrected projection along z direction.

        Raises
        ------
        NotImplementedError
            Child class should implemented this.
        """

        raise NotImplementedError("Child class should implemented this.")

    def getTempCorr(self):
        """Get the mirror print correction along z direction for certain
        temperature gradient.

        Returns
        ------
        numpy.ndarray
            Corrected projection along z direction.

        Raises
        ------
        NotImplementedError
            Child class should implemented this.
        """

        raise NotImplementedError("Child class should implemented this.")

    def getMirrorResInMmInZemax(self, gridFileName="", numTerms=28,
                                writeZcInMnToFilePath=None):
        """Get the residue of surface (mirror print along z-axis) in mm under
        the Zemax coordinate.

        This value is after the fitting with spherical Zernike polynomials
        (zk).

        Parameters
        ----------
        gridFileName : str, optional
            File name of bending mode data. (the default is "".)
        numTerms : {number}, optional
             Number of Zernike terms to fit. (the default is 28.)
        writeZcInMnToFilePath : str, optional
            File path to write the fitted zk in mm. (the default is None.)

        Returns
        ------
        numpy.ndarray
            Fitted residue in mm after removing the fitted zk terms in Zemax
            coordinate.
        numpy.ndarray
            X position in mm in Zemax coordinate.
        numpy.ndarray
            Y position in mm in Zemax coordinate.
        numpy.ndarray
            Fitted zk in mm in Zemax coordinate.

        Raises
        ------
        NotImplementedError
            Child class should implemented this.
        """

        raise NotImplementedError("Child class should implemented this.")

    def writeMirZkAndGridResInZemax(self, resFile="", surfaceGridN=200,
                                    gridFileName="", numTerms=28,
                                    writeZcInMnToFilePath=None):
        """Write the grid residue in mm of mirror surface after the fitting
        with Zk under the Zemax coordinate.

        Parameters
        ----------
        resFile : str or list, optional
            File path to save the grid surface residue map. (the default
            is "".)
        surfaceGridN : int, optional
            Surface grid number. (the default is 200.)
        gridFileName : str, optional
            File name of bending mode data. (the default is "".)
        numTerms : int, optional
            Number of Zernike terms to fit. (the default is 28.)
        writeZcInMnToFilePath : str, optional
            File path to write the fitted zk in mm. (the default is None.)

        Returns
        ------
        str
            Grid residue map related data.

        Raises
        ------
        NotImplementedError
            Child class should implemented this.
        """

        raise NotImplementedError("Child class should implemented this.")

    def showMirResMap(self, gridFileName="", numTerms=28, resFile=None,
                      writeToResMapFilePath=None):
        """Show the mirror residue map.

        Parameters
        ----------
        gridFileName : str, optional
            File name of bending mode data. (the default is "".)
        numTerms : int, optional
            Number of Zernike terms to fit. (the default is 28.)
        resFile : str or list, optional
            File path of the grid surface residue map. (the default is None.)
        writeToResMapFilePath : str or list, optional
            File path to save the residue map. (the default is None.)

        Raises
        ------
        NotImplementedError
            Child class should implemented this.
        """

        raise NotImplementedError("Child class should implemented this.")


if __name__ == "__main__":
    pass

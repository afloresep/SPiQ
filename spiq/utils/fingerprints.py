#This module provides functionality to compute molecular fingerprints from SMILES strings 
from multiprocessing import Pool
from functools import partial
from rdkit import Chem, DataStructs
import os 
from typing import List
import numpy as np
import numpy.typing as npt
import logging
from rdkit.Chem import rdFingerprintGenerator

logger = logging.getLogger(__name__)


def _calculate_morgan_fp(smiles: str, **params) -> np.array:
    """
    Calculate a Morgan fingerprint for a single SMILES string.

    This function uses RDKit to convert the input SMILES string into a molecular object,
    then computes the Morgan fingerprint based on the provided parameters.

    Args:
        smiles (str): A valid SMILES representation of a molecule.
        **params: Keyword parameters required for fingerprint calculation.
            Expected keys:
                - fpSize (int): Size of the fingerprint (number of bits).
                - radius (int): Radius parameter for the Morgan algorithm.

    Returns:
        np.array: An array representing the fingerprint.
            If the molecule conversion fails, a random fingerprint (with values 0 or 1) is returned.
            If an exception occurs during fingerprint calculation, None is returned.
    """
    fpSize = params.get('fpSize')
    radius = params.get('radius')
    if fpSize is None or radius is None:
        raise ValueError("Missing required parameters: 'fpSize' and/or 'radius'.")
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            logger.warning(f"SMILES '{smiles}' could not be converted to a molecule. Returning a random fingerprint.")
            return np.random.randint(0, 2, fpSize)
        fp = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=fpSize).GetFingerprint(mol)
        fp_arr = np.zeros((fpSize,), dtype=int)
        DataStructs.ConvertToNumpyArray(fp, fp_arr) 
        return fp_arr 
    except Exception as e:
        logger.error(f"Error processing SMILES '{smiles}': {e}")
        return None

class FingerprintCalculator:
    """
    A class to compute molecular fingerprints from a list of SMILES strings.
    Currently, only the 'morgan' fingerprint type is supported.
    """
    def __init__(self):
        
        # Map fingerprint types to functions
        self.fingerprint_function_map = {
            #TODO: Support for other fingerprints
            'morgan': _calculate_morgan_fp,
        }

    def FingerprintFromSmiles(self, smiles:List, fp:str, nprocesses:int = os.cpu_count(), **params) -> npt.NDArray:
        """
        Generate fingerprints for a list of SMILES strings in parallel.

        The method selects the appropriate fingerprint function based on the 'fp' parameter,
        binds additional keyword parameters using functools.partial, and then applies the function 
        across the SMILES list using multiprocessing.Pool.map.

        Args:
            smiles_list (list): A list of SMILES strings.
            fp (str): The fingerprint type to compute (e.g., 'morgan').
            nprocesses (int): Number of processes for multithreaded fingerprint calculation.  Default to cpu cores 
            **params: Additional keyword parameters for the fingerprint function.
                For 'morgan', required keys are:
                    - fpSize (int): Number of bits in the fingerprint.
                    - radius (int): Radius for the Morgan fingerprint.

        Returns:
            npt.NDArray: A NumPy array of fingerprints with shape (number of SMILES, fpSize).

        Raises:
            ValueError: If an unsupported fingerprint type is requested.
        """
        func = self.fingerprint_function_map.get(fp)
        if func is None:
            raise ValueError(f"Unsupported fingerprint type: '{fp}'")

        # Bind the additional parameters to the selected function.
        part_func = partial(func, **params)

        with Pool(processes=os.cpu_count()) as pool:
            fingerprints = pool.map(part_func, smiles)
        return np.array(fingerprints)
